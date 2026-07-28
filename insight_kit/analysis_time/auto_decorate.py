import importlib
import importlib.util
import inspect
import logging
import types
from contextvars import ContextVar

from .analysis import AT

logger = logging.getLogger("insight_kit.auto_decorate")

PIPELINE_TYPES = []

_diffusers_spec = importlib.util.find_spec("diffusers")
if _diffusers_spec:
    diffusers = importlib.import_module("diffusers")
    if hasattr(diffusers, "DiffusionPipeline"):
        PIPELINE_TYPES.append(diffusers.DiffusionPipeline)


PROCESS_NAMES = ("Porcess", "Process")
_call_state = ContextVar("ik_process_state", default=None)


class _CallState:
    def __init__(self):
        self.pre_started = False
        self.post_started = False


class PipelineProxy:
    def __init__(self, pipe):
        object.__setattr__(self, "_pipe", pipe)

    def __call__(self, *args, **kwargs):
        return _pipe_wrapper(self._pipe, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._pipe, name)

    def __setattr__(self, name, value):
        if name == "_pipe":
            object.__setattr__(self, name, value)
            return
        setattr(self._pipe, name, value)

    def __repr__(self):
        return f"PipelineProxy({self._pipe!r})"


def register_pipeline_type(pipeline_type):
    if pipeline_type not in PIPELINE_TYPES:
        PIPELINE_TYPES.append(pipeline_type)
    auto_install(pipeline_types=(pipeline_type,))


def _find_importer_globals():
    current_file = __file__
    for frame_info in inspect.stack():
        frame = frame_info.frame
        module_name = frame.f_globals.get("__name__", "")
        module_file = frame.f_globals.get("__file__")
        if module_file == current_file:
            continue
        if module_name.startswith("importlib"):
            continue
        return frame.f_globals
    return None


def _wrap_process(func):
    if getattr(func, "_ik_at_wrapped", False):
        return func

    def wrapped(*args, **kwargs):
        state = _CallState()
        token = _call_state.set(state)
        AT.begin_record("main")
        AT.begin_record("pre")
        state.pre_started = True
        try:
            return func(*args, **kwargs)
        finally:
            if state.post_started:
                AT.end_record("post")
            elif state.pre_started:
                AT.end_record("pre")
            AT.end_record("main")
            print(AT)
            _call_state.reset(token)

    wrapped._ik_at_wrapped = True
    return wrapped


def _pipe_wrapper(pipe, *args, **kwargs):
    state = _call_state.get()
    if state and state.pre_started and not state.post_started:
        AT.end_record("pre")
        state.pre_started = False
    AT.begin_record("pipe")
    try:
        return pipe(*args, **kwargs)
    finally:
        AT.end_record("pipe")
        if state and not state.post_started:
            AT.begin_record("post")
            state.post_started = True


def _wrap_pipeline(pipe):
    if isinstance(pipe, PipelineProxy):
        return pipe
    return PipelineProxy(pipe)


def _iter_children(obj):
    if isinstance(obj, dict):
        for item in obj.values():
            yield item
        return
    if isinstance(obj, (list, tuple, set)):
        for item in obj:
            yield item
        return
    try:
        attrs = vars(obj)
    except TypeError:
        attrs = {}
    for item in attrs.values():
        yield item
    slots = getattr(obj, "__slots__", ())
    if isinstance(slots, str):
        slots = (slots,)
    for slot in slots:
        try:
            yield getattr(obj, slot)
        except AttributeError:
            continue


def _find_pipeline_in_object(obj, pipeline_types, max_depth, visited):
    if max_depth <= 0:
        return None
    if isinstance(obj, (types.ModuleType, types.FunctionType, type)):
        return None
    obj_id = id(obj)
    if obj_id in visited:
        return None
    visited.add(obj_id)
    if isinstance(obj, dict):
        for attr_name, attr_value in obj.items():
            if isinstance(attr_value, pipeline_types):
                return obj, attr_name, attr_value
    else:
        try:
            attrs = vars(obj)
        except TypeError:
            attrs = {}
        for attr_name, attr_value in attrs.items():
            if isinstance(attr_value, pipeline_types):
                return obj, attr_name, attr_value
    for attr_value in _iter_children(obj):
        result = _find_pipeline_in_object(
            attr_value,
            pipeline_types,
            max_depth - 1,
            visited,
        )
        if result:
            return result
    return None


def _find_pipeline(globals_dict, pipeline_types, max_depth=3):
    for name, value in globals_dict.items():
        if isinstance(value, pipeline_types):
            return globals_dict, name, value
    visited = set()
    for _, value in globals_dict.items():
        result = _find_pipeline_in_object(value, pipeline_types, max_depth, visited)
        if result:
            return result
    return None


def auto_install(pipeline_types=None, process_names=None):
    if pipeline_types is None:
        pipeline_types = tuple(PIPELINE_TYPES)
    if process_names is None:
        process_names = PROCESS_NAMES
    caller_globals = _find_importer_globals()
    if not caller_globals:
        logger.warning(
            "auto_install() 未找到调用方全局变量（函数内 import？）；未做任何包裹"
        )
        return False
    wrapped = False
    for name in process_names:
        process_func = caller_globals.get(name)
        if callable(process_func):
            caller_globals[name] = _wrap_process(process_func)
            logger.info("auto_install() 已包裹 Process 函数 %r", name)
            wrapped = True
            break
    if pipeline_types:
        pipeline = _find_pipeline(caller_globals, pipeline_types)
        if pipeline:
            parent, attr_name, pipe_value = pipeline
            wrapped_pipe = _wrap_pipeline(pipe_value)
            if isinstance(parent, dict):
                parent[attr_name] = wrapped_pipe
            else:
                setattr(parent, attr_name, wrapped_pipe)
            logger.info("auto_install() 已包裹 pipeline %r", attr_name)
            wrapped = True
    if not wrapped:
        logger.warning(
            "auto_install() 未在调用方全局变量中找到 Process 函数或 pipeline，未做任何包裹"
        )
    return wrapped
