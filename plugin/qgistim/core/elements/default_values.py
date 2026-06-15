from dataclasses import dataclass


@dataclass
class DefaultValues:
    tmin: str = "0.01"
    order: str = "4"
    ndegrees: str = "6"
