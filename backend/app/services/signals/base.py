from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SignalResult:
    signal_type: str
    category: str
    value: float
    description: str


class BaseSignalProvider(ABC):
    @abstractmethod
    def fetch(self) -> list[SignalResult]:
        pass
