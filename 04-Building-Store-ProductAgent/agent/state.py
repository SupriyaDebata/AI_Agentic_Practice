from dataclasses import dataclass, field
from enum import Enum


class StopReason(Enum):
    """Reason why the agent stopped execution."""
    SUCCESS = "success"  # Request completed successfully
    OUT_OF_SCOPE = "out_of_scope"  # Request is outside store assistance scope
    UNRESOLVABLE = "unresolvable"  # Request couldn't be resolved despite tool calls
    MAX_ITERATIONS = "max_iterations"  # Reached iteration limit
    PRODUCT_NOT_FOUND = "product_not_found"  # Product doesn't exist
    UNKNOWN = "unknown"  # Default/unknown reason


@dataclass
class OrderItem:
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    final_price: float
    discount_percentage: float


@dataclass
class AgentState:
    messages: list[dict] = field(default_factory=list)
    order_items: list[OrderItem] = field(default_factory=list)
    order_total: float = 0.0
    destination_pincode: str | None = None
    # Remember pending product/quantity across turns (e.g. user gives PIN in a follow-up)
    pending_product: str | None = None
    pending_quantity: int | None = None
    trace: list[dict] = field(default_factory=list)
    iteration_count: int = 0
    stop_reason: StopReason = StopReason.UNKNOWN
    refusal_message: str | None = None  # Grounded explanation for why we're stopping

    def add_order_item(self, item: OrderItem) -> None:
        self.order_items = [i for i in self.order_items if i.product_id != item.product_id]
        self.order_items.append(item)
        self.order_total = sum(i.final_price for i in self.order_items)

    def add_trace_step(self, tool: str, input_data: dict, result: dict) -> None:
        self.trace.append({"tool": tool, "input": input_data, "result": result})

    def order_summary(self) -> str:
        """Return a plain-text summary of the current order for context injection."""
        if not self.order_items and not self.pending_product:
            return "No items in the current order."
        lines = []
        for item in self.order_items:
            lines.append(f"- {item.product_name} × {item.quantity} = ₹{item.final_price:,.2f}")
        if self.order_total:
            lines.append(f"Order total so far: ₹{self.order_total:,.2f}")
        if self.pending_product:
            qty = self.pending_quantity or "unknown"
            lines.append(f"Pending (not yet priced): {self.pending_product} × {qty}")
        if self.destination_pincode:
            lines.append(f"Delivery PIN code: {self.destination_pincode}")
        return "\n".join(lines) if lines else "No items in the current order."
