from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from typing import List

        
# -------- Agent Data ------------ #
@dataclass
class TrajectoryStep:
    x: float = 0
    y: float = 0
    z: float = 0
    orientations: List[float] = field(default_factory=list)
    time: float = 0


@dataclass
class Destination:
    x: float = 0
    y: float = 0
    z: float = 0
    orientations: List[float] = field(default_factory=list)


@dataclass_json    
@dataclass
class RequestBody:
   destination: Destination
   trajectory: List[TrajectoryStep]