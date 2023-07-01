from dataclasses import dataclass
from typing import Any, Dict, Generator, Optional, Set
from abc import ABC, abstractmethod
import os
from pydantic import ConfigDict, BaseModel


@dataclass
class Prompt:
    prompt: str
    model: "Model"
    system: Optional[str]
    prompt_json: Optional[str]
    options: Dict[str, Any]

    def __init__(self, prompt, model, system=None, prompt_json=None, options=None):
        self.prompt = prompt
        self.model = model
        self.system = system
        self.prompt_json = prompt_json
        self.options = options or {}


class OptionsError(Exception):
    pass


class Response(ABC):
    def __init__(self, prompt: Prompt, model: "Model", stream: bool):
        self.prompt = prompt
        self.model = model
        self.stream = stream
        self._chunks = []
        self._debug = {}
        self._done = False

    def __iter__(self):
        if self._done:
            return self._chunks
        for chunk in self.iter_prompt():
            yield chunk
            self._chunks.append(chunk)
        self._done = True

    @abstractmethod
    def iter_prompt(self) -> Generator[str, None, None]:
        pass

    def _force(self):
        if not self._done:
            list(self)

    def text(self):
        self._force()
        return "".join(self._chunks)


class Model(ABC):
    model_id: str
    key: Optional[str] = None
    needs_key: Optional[str] = None
    key_env_var: Optional[str] = None
    can_stream: bool = False

    class Options(BaseModel):
        model_config = ConfigDict(extra="forbid")

    def get_key(self):
        if self.needs_key is None:
            return None
        if self.key is not None:
            return self.key
        if self.key_env_var is not None:
            return os.environ.get(self.key_env_var)
        return None

    def prompt(self, prompt, system=None, **options):
        return self.execute(
            Prompt(prompt, system=system, model=self, options=self.Options(**options)),
            stream=False,
        )

    def stream(self, prompt, system=None, **options):
        return self.execute(
            Prompt(prompt, system=system, model=self, options=self.Options(**options)),
            stream=True,
        )

    @abstractmethod
    def execute(self, prompt: Prompt, stream: bool = True) -> Response:
        pass

    @abstractmethod
    def __str__(self) -> str:
        pass


@dataclass
class ModelWithAliases:
    model: Model
    aliases: Set[str]
