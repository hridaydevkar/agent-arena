"""Run: arena run examples/revenue_agent.py --task revenue-by-region --submit"""

from agent_arena import Agent, AgentResult, Task, ToolContext


class RevenueAgent(Agent):
    def run(self, task: Task, tools: ToolContext) -> AgentResult:
        if task.id != "revenue-by-region":
            raise ValueError("This example only handles the revenue-by-region task")
        orders = tools.read_file("orders")
        tools.note("Exclude cancelled orders and aggregate net revenue by region.")

        def aggregate():
            totals = {}
            for row in orders:
                if row["status"] == "cancelled":
                    continue
                region = row["region"]
                totals[region] = totals.get(region, 0) + row["amount"] - row["refund"]
            return totals

        totals = tools.record("tool", "revenue.aggregate", {"rows": len(orders)}, aggregate)
        best = sorted(totals, key=lambda region: (-totals[region], region))[0]
        output = {
            "total_net_revenue": sum(totals.values()),
            "top_region": best,
            "top_region_revenue": totals[best],
        }
        tools.record("output", "agent.result", {}, lambda: output)
        return AgentResult(output=output, summary="Net revenue excludes cancelled orders and subtracts refunds.")
