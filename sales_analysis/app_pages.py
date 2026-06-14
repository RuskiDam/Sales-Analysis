import json
import time

import pandas as pd
import streamlit as st

from sales_analysis.ai.ai_service import AIService
from sales_analysis.ai.llm_client import LLMClient
from sales_analysis.ai.rag_pipeline import HaystackRAGPipeline, RAGCorpus
from sales_analysis.data.sales_data import DisplayFormatter
from sales_analysis.reports.monthly_pdf import MonthlyPDFReport


@st.dialog("RAG documents")
def show_rag_documents_dialog(rows):
    if not rows:
        st.warning("No predefined RAG documents found.")
        return

    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
    )


class BasePage:
    message_lifetime_seconds = 5
    positive_color = "#1f883d"
    negative_color = "#cf222e"
    revenue_color = "#0969da"

    def __init__(self, data_store, metrics, finance_policy, action_logger):
        self.data_store = data_store
        self.metrics = metrics
        self.finance_policy = finance_policy
        self.action_logger = action_logger

    def load_sales_rows(self, file_path, label):
        return self.load_json_data(
            self.data_store.load_sales_rows,
            file_path,
            label,
        )

    def load_inventory_rows(self, file_path, label):
        return self.load_json_data(
            self.data_store.load_inventory_rows,
            file_path,
            label,
        )

    @staticmethod
    def load_json_data(loader, file_path, label):
        try:
            return loader(file_path)
        except FileNotFoundError:
            st.error(f"Missing {label} file.")
        except json.JSONDecodeError:
            st.error(f"{label.title()} file is not valid JSON.")
        except ValueError as error:
            st.error(str(error))

        return None

    def show_metric_grid(self, metrics, columns_per_row=3):
        for start in range(0, len(metrics), columns_per_row):
            columns = st.columns(columns_per_row)
            row_metrics = metrics[start:start + columns_per_row]
            for column, metric in zip(columns, row_metrics):
                with column:
                    st.metric(
                        metric["label"],
                        metric["value"],
                        delta=metric.get("delta"),
                        delta_color=metric.get("delta_color", "normal"),
                        border=True,
                    )

    def show_finance_sheet(self, finance):
        """Render company deductions with status styling for financial health."""

        st.subheader("Company Deductions")
        styled_finance = self.finance_frame(finance).style.map(
            self.status_style,
            subset=["Status"],
        )
        st.dataframe(
            styled_finance,
            hide_index=True,
            width="stretch",
            column_config={
                "Datatype": st.column_config.TextColumn("Datatype"),
                "Value": st.column_config.TextColumn("Value"),
                "Status": st.column_config.TextColumn("Status"),
            },
        )

    def finance_frame(self, finance):
        rows = self.finance_rows(finance)
        frame = pd.DataFrame(rows, columns=["Datatype", "Value", "Status"])
        frame = frame.round(2)
        frame["Value"] = frame["Value"].map(DisplayFormatter.money)
        return frame

    def finance_rows(self, finance):
        return [
            ("Staff Payroll", finance["staff_payroll"], "↓ Negative"),
            ("Health Insurance", finance["health_insurance"], "↓ Negative"),
            ("Taxes", finance["taxes"], "↓ Negative"),
            ("Break Even Margin", finance["break_even_margin"], "= Neutral"),
            (
                "Net Income",
                finance["net_income"],
                self.status_label(
                    finance["net_income"],
                    finance["break_even_margin"],
                ),
            ),
        ]

    def status_label(self, value, target):
        if value > target:
            return "↑ Positive"

        if value < target:
            return "↓ Negative"

        return "= Neutral"

    def status_style(self, value):
        if value.startswith("↑"):
            return (
                "background-color: #dafbe1; color: #116329; "
                "font-weight: 700;"
            )

        if value.startswith("↓"):
            return (
                "background-color: #ffebe9; color: #82071e; "
                "font-weight: 700;"
            )

        if value.startswith("="):
            return (
                "background-color: #f6f8fa; color: #57606a; "
                "font-weight: 700;"
            )

        return ""

    def delta_color(self, value, target):
        if value == target:
            return "off"

        return "normal"

    def signed_delta(self, value, target, formatter=DisplayFormatter.percent):
        if value == target:
            return "= Neutral"

        difference = value - target
        if difference > 0:
            return f"+{formatter(difference)}"

        return formatter(difference)

    def shipping_delta(self, value):
        if value == 0:
            return "= Neutral"

        return f"-{DisplayFormatter.money(value)}"

    def profit_margin_metric(self, profit_margin):
        return {
            "label": "Profit Margin",
            "value": DisplayFormatter.percent(profit_margin),
            "delta": self.signed_delta(
                profit_margin,
                self.finance_policy.average_profit_margin,
            ),
            "delta_color": self.delta_color(
                profit_margin,
                self.finance_policy.average_profit_margin,
            ),
        }

    def mom_growth_metric(self, label, revenue_growth):
        return {
            "label": label,
            "value": DisplayFormatter.percent(revenue_growth),
            "delta": self.signed_delta(
                revenue_growth,
                self.finance_policy.average_mom_growth,
            ),
            "delta_color": self.delta_color(
                revenue_growth,
                self.finance_policy.average_mom_growth,
            ),
        }

    def shipping_metric(self, label, shipping_costs):
        return {
            "label": label,
            "value": DisplayFormatter.money(shipping_costs),
            "delta": self.shipping_delta(shipping_costs),
            "delta_color": self.delta_color(shipping_costs, 0),
        }

    def net_income_metric(self, finance):
        return {
            "label": "Net Income",
            "value": DisplayFormatter.money(finance["net_income"]),
            "delta": self.signed_delta(
                finance["net_income"],
                finance["break_even_margin"],
                DisplayFormatter.money,
            ),
            "delta_color": self.delta_color(
                finance["net_income"],
                finance["break_even_margin"],
            ),
        }


class CalculatorPage(BasePage):
    def __init__(
        self,
        data_store,
        metrics,
        finance_policy,
        action_logger,
        simulation_manager,
        historical_simulator,
    ):
        super().__init__(
            data_store,
            metrics,
            finance_policy,
            action_logger,
        )
        self.simulation_manager = simulation_manager
        self.historical_simulator = historical_simulator

    def show(self):
        st.title("Sales Calculator")
        st.write(
            "Sales calculator view will calculate profit and growth metrics."
        )
        if not self.ensure_simulation_files():
            return

        self.show_reset_controls()
        self.show_app_messages()
        self.show_simulation_controls()
        self.show_monthly_report()

    def ensure_simulation_files(self):
        try:
            self.simulation_manager.ensure_baselines()
        except FileNotFoundError as error:
            st.error(str(error))
            return False

        return True

    def show_reset_controls(self):
        if st.button(
            "Reset",
            help=(
                "Restores simulation inventory and sales history back to "
                "their saved starting versions."
            ),
        ):
            self.simulation_manager.reset_files()
            self.action_logger.log("user", "reset_simulation")
            self.add_app_message("reset", "Simulation data reset.")
            st.rerun()

    @staticmethod
    def add_app_message(message_key, message):
        if "app_messages" not in st.session_state:
            st.session_state.app_messages = {}

        st.session_state.app_messages[message_key] = {
            "message": message,
            "time": time.time(),
        }

    def show_simulation_controls(self):
        st.subheader("Historical Simulation")
        first_column, second_column = st.columns(2)

        with first_column:
            if st.button("Run 6-month simulation", width="stretch"):
                self.run_historical_simulation(6)

        with second_column:
            if st.button("Run 12-month simulation", width="stretch"):
                self.run_historical_simulation(12)

    def run_historical_simulation(self, month_count):
        """Run simulation, report user-facing errors, and log successful runs."""

        try:
            summary = self.historical_simulator.run(month_count)
        except FileNotFoundError:
            self.show_simulation_error(
                month_count,
                "Missing simulation inventory or sales file.",
            )
            return
        except json.JSONDecodeError:
            self.show_simulation_error(
                month_count,
                "Simulation inventory or sales file is not valid JSON.",
            )
            return
        except ValueError as error:
            self.show_simulation_error(month_count, str(error))
            return

        self.log_simulation_success(month_count, summary)
        self.show_simulation_success(month_count, summary)
        st.rerun()

    def log_simulation_success(self, month_count, summary):
        self.action_logger.log(
            "user",
            "run_historical_simulation",
            "success",
            {
                "months": month_count,
                "orders": summary["orders"],
                "items": summary["items"],
                "revenue": summary["revenue"],
            },
        )

    def show_simulation_success(self, month_count, summary):
        self.add_app_message(
            "history",
            (
                f"Generated {month_count} months: "
                f"{summary['orders']} orders, {summary['items']} items sold, "
                f"{DisplayFormatter.money(summary['revenue'])} revenue."
            ),
        )

    def show_simulation_error(self, month_count, message):
        self.log_simulation_error(month_count, message)
        st.error(message)

    def log_simulation_error(self, month_count, message):
        self.action_logger.log(
            "app",
            "run_historical_simulation",
            "error",
            {"months": month_count, "message": message},
        )

    @st.fragment(run_every="1s")
    def show_app_messages(self):
        """Display short-lived success messages stored in Streamlit session state."""

        messages = st.session_state.get("app_messages", {})
        if not messages:
            return

        for message_key in list(messages.keys()):
            message_data = messages[message_key]
            elapsed_seconds = int(time.time() - message_data["time"])
            seconds_remaining = self.message_lifetime_seconds - elapsed_seconds

            if seconds_remaining <= 0:
                del messages[message_key]
            else:
                st.success(f"{message_data['message']} ({seconds_remaining}s)")

        st.session_state.app_messages = messages

    def show_monthly_report(self):
        """Load current simulation files and render the newest monthly report."""

        if st.button("Generate Monthly Report"):
            self.action_logger.log("user", "generate_monthly_report")
            st.session_state.show_monthly_report = True

        if not st.session_state.get("show_monthly_report", False):
            return

        inventory_rows, sales_rows = self.report_data()
        if inventory_rows is None or sales_rows is None:
            return

        report = self.latest_report(sales_rows)
        if report is None:
            st.warning("No sales data available for a monthly report.")
            return

        self.render_monthly_report(report, inventory_rows)

    def report_data(self):
        inventory_rows = self.load_inventory_rows(
            "simulation/sb_inventory.json",
            "simulation inventory",
        )
        sales_rows = self.load_sales_rows(
            "simulation/sb_sales_log.json",
            "simulation sales",
        )
        return inventory_rows, sales_rows

    def latest_report(self, sales_rows):
        return self.metrics.latest_month_report(
            sales_rows,
            self.finance_policy,
        )

    def render_monthly_report(self, report, inventory_rows):
        st.subheader(
            f"Monthly Report: "
            f"{self.metrics.month_label(report['year'], report['month'])}"
        )
        report_metrics = self.monthly_report_metrics(report, inventory_rows)
        self.show_metric_grid(report_metrics)
        self.show_finance_sheet(report["finance"])

    def monthly_report_metrics(self, report, inventory_rows):
        """Convert a latest-month report into Streamlit metric definitions."""

        finance = report["finance"]
        items_sold = self.metrics.sold_quantity(report["current_sales"])
        warehouse_value = self.metrics.inventory_value(inventory_rows)
        metrics = self.monthly_money_metrics(report, finance)
        metrics.extend(
            [
                {
                    "label": "Items sold",
                    "value": f"{items_sold:,d}",
                },
                {
                    "label": "Warehouse value",
                    "value": DisplayFormatter.money(warehouse_value),
                },
                self.shipping_metric(
                    "Total shipping cost",
                    report["shipping_costs"],
                ),
            ]
        )
        return metrics

    def monthly_money_metrics(self, report, finance):
        return [
            {
                "label": "Revenue",
                "value": DisplayFormatter.money(report["current_revenue"]),
            },
            {
                "label": "Profit after shipping",
                "value": DisplayFormatter.money(finance["gross_profit"]),
            },
            self.profit_margin_metric(report["profit_margin"]),
            self.mom_growth_metric("MoM growth", report["revenue_growth"]),
        ]


class InventoryPage(BasePage):
    def show(self):
        st.title("Inventory")
        st.write(
            "Inventory view will show current inventory and past purchases. "
            "It will also show frequency of purchased products."
        )
        self.show_inventory_table(
            "simulation/sb_inventory.json",
            "simulation/sb_sales_log.json",
            show_warehouse_value=False,
        )

    def show_inventory_table(
        self,
        file_path,
        sales_file_path,
        show_warehouse_value,
    ):
        """Load inventory/sales data and render dashboard plus inventory sheet."""

        rows = self.load_inventory_rows(file_path, "inventory")
        sales_rows = self.load_sales_rows(sales_file_path, "sales")
        if rows is None or sales_rows is None:
            return

        self.show_inventory_dashboard(rows, sales_rows, show_warehouse_value)
        st.subheader("Inventory Sheet")
        self.show_inventory_frame(rows)

    def show_inventory_frame(self, rows):
        styled_inventory = self.inventory_frame(rows).style.map(
            DisplayFormatter.availability_style,
            subset=["Available"],
        )
        st.dataframe(
            styled_inventory,
            hide_index=True,
            width="stretch",
            column_config={
                "Price": st.column_config.TextColumn("Price"),
                "Quantity": st.column_config.TextColumn("Quantity"),
                "Available": st.column_config.TextColumn("Available"),
            },
        )

    @staticmethod
    def inventory_frame(rows):
        frame = pd.DataFrame(rows)
        frame["Price"] = frame["Price"].map(DisplayFormatter.money)
        frame["Quantity"] = frame["Quantity"].map(lambda value: f"{value:,d}")
        return frame

    def show_inventory_dashboard(self, rows, sales_rows, show_warehouse_value):
        if show_warehouse_value:
            columns = st.columns(3)
            self.show_warehouse_metric(columns[0], rows)
            sold_column, revenue_column = columns[1], columns[2]
        else:
            sold_column, revenue_column = st.columns(2)

        self.show_sold_metric(sold_column, sales_rows)
        self.show_revenue_metric(revenue_column, sales_rows)

    def show_warehouse_metric(self, column, rows):
        with column:
            st.subheader("Warehouse Value")
            st.metric(
                "Inventory value",
                DisplayFormatter.money(self.metrics.inventory_value(rows)),
                border=True,
            )

    def show_sold_metric(self, column, sales_rows):
        with column:
            st.subheader("Products Sold")
            st.metric(
                "Items sold",
                self.metrics.sold_quantity(sales_rows),
                border=True,
            )

    def show_revenue_metric(self, column, sales_rows):
        with column:
            st.subheader("Money Gained")
            st.metric(
                "Revenue",
                DisplayFormatter.money(self.metrics.sales_revenue(sales_rows)),
                border=True,
            )


class AnalysisPage(BasePage):
    def show(self):
        st.title("Analysis")
        st.write(
            "Analysis view will show how our company is performing via "
            "sales and inventory."
        )
        sales_rows = self.load_sales_rows(
            "simulation/sb_sales_log.json",
            "simulation sales",
        )
        if sales_rows is None:
            return

        self.show_analysis_summary(sales_rows)
        self.show_analysis_trends(sales_rows)

    def show_analysis_summary(self, sales_rows):
        """Render high-level financial metrics plus the deductions sheet."""

        metrics, finance = self.analysis_summary_metrics(sales_rows)
        self.show_metric_grid(metrics)
        self.show_finance_sheet(finance)

    def analysis_summary_metrics(self, sales_rows):
        """Build the metric cards and finance data for the Analysis header."""

        values = self.analysis_values(sales_rows)
        metrics = [
            {
                "label": "Total Revenue",
                "value": DisplayFormatter.money(values["total_revenue"]),
            },
            self.profit_margin_metric(values["profit_margin"]),
            {"label": "Total Orders", "value": f"{len(sales_rows):,d}"},
        ]
        metrics.extend(
            self.analysis_status_metrics(
                values["shipping_costs"],
                values["revenue_growth"],
                values["finance"],
            )
        )
        return metrics, values["finance"]

    def analysis_values(self, sales_rows):
        """Calculate reusable totals for Analysis page metrics."""

        total_revenue = self.metrics.sales_revenue(sales_rows)
        shipping_costs = self.metrics.shipping_costs(sales_rows)
        month_count = len(self.metrics.monthly_totals(sales_rows))
        finance = self.finance_policy.financial_summary(
            total_revenue,
            shipping_costs,
            month_count,
        )
        return {
            "total_revenue": total_revenue,
            "shipping_costs": shipping_costs,
            "finance": finance,
            "profit_margin": self.metrics.profit_margin(
                finance["net_income"],
                total_revenue,
            ),
            "revenue_growth": self.month_over_month_growth(sales_rows),
        }

    def analysis_status_metrics(
        self,
        shipping_costs,
        revenue_growth,
        finance,
    ):
        return [
            self.shipping_metric("Shipping Costs", shipping_costs),
            self.mom_growth_metric("MoM Revenue Growth", revenue_growth),
            self.net_income_metric(finance),
        ]

    def show_analysis_trends(self, sales_rows):
        """Render monthly trend charts and table from simulation sales rows."""

        monthly_rows = self.metrics.monthly_financials(
            sales_rows,
            self.finance_policy,
        )
        if not monthly_rows:
            st.warning("No sales data yet. Run Historical Simulation first.")
            return

        breakdown_frame, revenue_frame, shipping_frame = (
            self.analysis_frames(monthly_rows)
        )
        self.show_revenue_chart(revenue_frame)
        self.show_shipping_chart(shipping_frame)
        self.show_monthly_breakdown(breakdown_frame)

    @staticmethod
    def analysis_frames(monthly_rows):
        """Prepare chart frames for revenue/profit and shipping impact."""

        breakdown_frame = pd.DataFrame(monthly_rows).round(2)
        trend_frame = breakdown_frame.copy()
        trend_frame["Shipping Impact"] = (
            -trend_frame["Shipping Costs"]
        ).round(2)
        trend_frame["Profit Positive"] = trend_frame["Profit"].where(
            trend_frame["Profit"] >= 0
        ).round(2)
        trend_frame["Profit Negative"] = trend_frame["Profit"].where(
            trend_frame["Profit"] < 0
        ).round(2)
        revenue_frame = trend_frame[
            ["Month", "Revenue", "Profit Positive", "Profit Negative"]
        ]
        shipping_frame = trend_frame[["Month", "Shipping Impact"]]
        return breakdown_frame, revenue_frame, shipping_frame

    def show_revenue_chart(self, revenue_frame):
        st.subheader("Revenue/Profit Trend")
        st.line_chart(
            revenue_frame,
            x="Month",
            y=["Revenue", "Profit Positive", "Profit Negative"],
            color=[
                self.revenue_color,
                self.positive_color,
                self.negative_color,
            ],
            width="stretch",
            y_label="Dollars",
        )

    def show_shipping_chart(self, shipping_frame):
        st.subheader("Shipping Cost Impact")
        st.bar_chart(
            shipping_frame,
            x="Month",
            y="Shipping Impact",
            color=self.negative_color,
            width="stretch",
            y_label="Dollars",
        )

    def show_monthly_breakdown(self, breakdown_frame):
        st.subheader("Monthly Breakdown")
        st.dataframe(
            self.formatted_monthly_frame(breakdown_frame),
            hide_index=True,
            width="stretch",
        )

    @staticmethod
    def formatted_monthly_frame(frame):
        """Format monthly financial rows for display without changing source data."""

        display_frame = frame.copy()
        money_columns = [
            "Revenue",
            "Profit",
            "Gross Profit",
            "Shipping Costs",
            "Staff Payroll",
            "Health Insurance",
            "Break Even Margin",
            "Taxes",
        ]
        for column in money_columns:
            display_frame[column] = display_frame[column].map(
                DisplayFormatter.money
            )

        display_frame["Orders"] = display_frame["Orders"].map(
            lambda value: f"{value:,d}"
        )
        return display_frame

    def month_over_month_growth(self, sales_rows):
        """Compare latest month revenue against the immediately prior month."""

        latest_month = self.metrics.latest_sales_month(sales_rows)
        if latest_month is None:
            return 0.0

        year, month = latest_month
        previous_year, previous_month = self.metrics.previous_month(
            year,
            month,
        )
        current_sales = self.metrics.sales_for_month(sales_rows, year, month)
        previous_sales = self.metrics.sales_for_month(
            sales_rows,
            previous_year,
            previous_month,
        )
        current_revenue = self.metrics.sales_revenue(current_sales)
        previous_revenue = self.metrics.sales_revenue(previous_sales)
        return self.metrics.mom_revenue_growth(
            current_revenue,
            previous_revenue,
        )


class AIPage(BasePage):
    def show(self):
        st.markdown('<div class="ai-page">', unsafe_allow_html=True)
        self.show_header()
        self.ensure_ai_messages()
        if not st.session_state.ai_messages:
            self.show_ai_empty_state()

        self.show_ai_chat_history()
        prompt = st.chat_input(
            "Ask about revenue, profit, growth, shipping, or inventory"
        )
        if prompt:
            self.handle_ai_prompt(prompt)

        st.markdown("</div>", unsafe_allow_html=True)

    def show_header(self):
        header_column, docs_column, clear_column = st.columns(
            [0.72, 0.14, 0.14]
        )
        with header_column:
            st.title("Sales A.I.")
        with docs_column:
            self.show_rag_document_status()
        with clear_column:
            if st.button("Clear", width="stretch"):
                st.session_state.ai_messages = []
                self.action_logger.log("user", "clear_ai_chat")
                st.rerun()

    def ensure_ai_messages(self):
        if "ai_messages" not in st.session_state:
            st.session_state.ai_messages = []

    def show_ai_empty_state(self):
        st.markdown(
            """
            <div class="ai-empty-state">
                <h2>Ask about current sales performance</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )

    def show_ai_chat_history(self):
        for index, message in enumerate(st.session_state.ai_messages):
            with st.chat_message(message["role"]):
                st.write(message["content"])
                report = message.get("report")
                if report:
                    self.show_report_download(report, index)
                references = message.get("references", [])
                if references:
                    self.show_references(references)

    def show_rag_document_status(self):
        rows = self.rag_document_rows()
        button_pressed = st.button("RAG", width="stretch")
        if button_pressed:
            show_rag_documents_dialog(rows)

    @staticmethod
    @st.cache_data
    def rag_document_rows():
        return [
            {
                "Document": source["source"],
                "Size KB": source["size_kb"],
            }
            for source in RAGCorpus().sources()
        ]

    def show_references(self, references):
        st.caption("References")
        st.dataframe(
            pd.DataFrame(references),
            hide_index=True,
            width="stretch",
        )

    def handle_ai_prompt(self, prompt):
        """Append user prompt, call A.I. service, and persist assistant response."""

        client = LLMClient()
        model = client.model or ""
        prior_messages = list(st.session_state.ai_messages)
        self.append_ai_message("user", prompt)
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking"):
                result = self.ai_result(prompt, model, prior_messages)
            st.write(result["answer"])
            if result.get("report"):
                self.show_report_download(result["report"], len(prior_messages))
            if result["references"]:
                self.show_references(result["references"])

        self.append_ai_message(
            "assistant",
            result["answer"],
            result["references"],
            result.get("report"),
        )

    def append_ai_message(self, role, content, references=None, report=None):
        message = {"role": role, "content": content}
        if references:
            message["references"] = references
        if report:
            message["report"] = report

        st.session_state.ai_messages.append(message)

    def ai_result(self, prompt, model, chat_history=None):
        """Call A.I. service and log success or safe error details."""

        if self.is_pdf_report_request(prompt):
            return self.pdf_report_result(prompt, model, chat_history)

        try:
            rag_result = AIService(
                self.data_store,
                self.metrics,
                self.finance_policy,
                rag_pipeline=self.rag_pipeline(),
            ).answer(prompt, model, chat_history)
        except ValueError as error:
            self.log_ai_result("app", model, prompt, "error", str(error))
            return {"answer": str(error), "references": []}

        self.log_ai_result(
            "user",
            model,
            prompt,
            "success",
            references=len(rag_result.documents),
        )
        return {
            "answer": rag_result.answer,
            "references": rag_result.references(),
        }

    @staticmethod
    def is_pdf_report_request(prompt):
        normalized_prompt = prompt.lower()
        asks_for_file = "pdf" in normalized_prompt or "report" in normalized_prompt
        asks_for_business_report = any(
            term in normalized_prompt
            for term in ("mom", "monthly", "sales", "fiscal")
        )
        return asks_for_file and asks_for_business_report

    def pdf_report_result(self, prompt, model, chat_history=None):
        try:
            report = MonthlyPDFReport(
                self.data_store,
                self.metrics,
                self.finance_policy,
            ).build(chat_history)
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as error:
            self.log_ai_result("app", model, prompt, "error", str(error))
            return {"answer": str(error), "references": []}

        self.log_ai_result(
            "user",
            model,
            prompt,
            "success",
            message="generated_pdf_report",
        )
        return {
            "answer": (
                "Generated a monthly Sales/Fiscal PDF report from current "
                "simulation data and recent chat context."
            ),
            "references": [{"Document": "docs/Professional-PDF-Style.md"}],
            "report": report,
        }

    @staticmethod
    def show_report_download(report, index):
        st.download_button(
            "Download Monthly Sales/Fiscal PDF",
            data=report["data"],
            file_name=report["file_name"],
            mime=report["mime"],
            key=f"monthly_pdf_download_{index}",
            width="stretch",
        )

    def log_ai_result(
        self,
        actor,
        model,
        prompt,
        status,
        message="",
        references=0,
    ):
        """Log A.I. metadata without storing the user's prompt text."""

        details = {
            "model": model,
            "prompt_chars": len(prompt),
        }
        if message:
            details["message"] = message
        if references:
            details["references"] = references

        self.action_logger.log(actor, "ask_ai", status, details)

    @staticmethod
    @st.cache_resource
    def rag_pipeline():
        return HaystackRAGPipeline()
