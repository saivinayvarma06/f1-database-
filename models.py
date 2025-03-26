from pydantic import BaseModel

# Driver Schema
class Driver(BaseModel):
    name: str
    age: int
    total_pole_positions: int
    total_race_wins: int
    total_points_scored: int
    total_world_titles: int
    total_fastest_laps: int
    team: str

# Team Schema
class Team(BaseModel):
    name: str
    year_founded: int
    total_pole_positions: int
    total_race_wins: int
    total_constructor_titles: int
    finishing_position_last_season: int


class DriverDeleteRequest(BaseModel):
    name: str