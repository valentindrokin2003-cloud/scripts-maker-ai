from dataclasses import dataclass, field
from typing import List, Optional
import re
from unidecode import unidecode


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

    @property
    def name_en(self) -> str:
        """Transliterate name to ASCII for use in table names (Cyrillic → Latin)."""
        # Transliterate Russian to Latin, replace spaces with underscores
        s = unidecode(self.name)
        s = s.replace(" ", "_")
        s = re.sub(r'[/\\:*?"<>|]', "_", s)
        # Remove apostrophes and other punctuation
        s = re.sub(r"['\-]", "", s)
        # Remove consecutive underscores
        s = re.sub(r"_+", "_", s)
        # Remove leading/trailing underscores
        s = s.strip("_")
        return s
