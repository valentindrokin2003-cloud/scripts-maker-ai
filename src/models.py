from dataclasses import dataclass, field
from typing import List, Optional
import re


@dataclass
class BriefData:
    # Required
    name: str
    inn_client: List[str]
    analysis_period: str  # normalised form: "last_N_months:6" or "range:YYYY-MM-DD:YYYY-MM-DD"

    # Optional with defaults
    product_words: List[str] = field(default_factory=list)
    regions: List[str] = field(default_factory=list)
    okved_list: List[str] = field(default_factory=list)
    exclusions: List[str] = field(default_factory=list)
    revenue_min: int = 100_000_000
    revenue_max: Optional[int] = None
    trans_sum_min: int = 10_000_000
    trans_cnt_min: int = 3

    @property
    def name_safe(self) -> str:
        """Sanitise name for use as a filename component."""
        s = self.name.replace(" ", "_")
        s = re.sub(r'[/\\:*?"<>|]', "_", s)
        return s
