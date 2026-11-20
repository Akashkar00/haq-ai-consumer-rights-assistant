from datetime import date as Date
from enum import Enum

from pydantic import BaseModel, Field


class IssueType(str, Enum):
    non_delivery = "non_delivery"
    damaged_item = "damaged_item"
    defective_item = "defective_item"
    wrong_item = "wrong_item"
    cancelled_not_refunded = "cancelled_not_refunded"
    return_refused = "return_refused"
    other = "other"


class PartyType(str, Enum):
    seller = "seller"
    platform = "platform"
    both = "both"
    unknown = "unknown"


class PaymentMode(str, Enum):
    upi = "upi"
    card = "card"
    netbanking = "netbanking"
    cod = "cod"
    wallet = "wallet"
    other = "other"


class Party(BaseModel):
    name: str | None = None
    type: PartyType = PartyType.unknown


class TimelineEvent(BaseModel):
    date: Date | None = None
    event: str
    source: str = "user_stated"


class Complaint(BaseModel):
    date: Date | None = None
    channel: str | None = None
    ticket_id: str | None = None
    response: str | None = None


class Evidence(BaseModel):
    type: str  # invoice | screenshot | email | photo | bank_statement | chat | other
    available: bool = True


class Location(BaseModel):
    state: str | None = None
    district: str | None = None


class CaseFile(BaseModel):
    issue_type: IssueType | None = None
    opposite_party: Party = Field(default_factory=Party)
    platform: str | None = None
    product_or_service: str | None = None
    order_id: str | None = None
    order_date: Date | None = None
    amount_paid_inr: float | None = None
    payment_mode: PaymentMode | None = None
    timeline: list[TimelineEvent] = Field(default_factory=list)
    complaints_made: list[Complaint] = Field(default_factory=list)
    no_complaint_yet: bool = False
    evidence: list[Evidence] = Field(default_factory=list)
    remedy_sought: str | None = None
    user_location: Location | None = None
    notes_uncertain: list[str] = Field(default_factory=list)
    user_confirmed: bool = False


class Option(BaseModel):
    step: str
    why: str


class Explanation(BaseModel):
    summary: str
    options: list[Option] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    needs_lawyer: bool = False
    lawyer_reason: str | None = None
