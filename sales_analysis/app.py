import streamlit as st

from sales_analysis.app_pages import (
    AIPage,
    AnalysisPage,
    CalculatorPage,
    InventoryPage,
)
from sales_analysis.app_styles import AppStyles
from sales_analysis.data.sales_data import SalesDataStore, SalesMetrics
from sales_analysis.finance.company_finance import CompanyFinancePolicy
from sales_analysis.logging.app_logger import AppActionLogger
from sales_analysis.simulation.historical_simulator import (
    HistoricalSalesSimulator,
)
from sales_analysis.simulation.simulation_files import SimulationFileManager


class StreamlitSalesApp:
    nav_items = {
        "calculator": {
            "label": "Calculator",
            "icon": ":material/calculate:",
        },
        "inventory": {
            "label": "Inventory",
            "icon": ":material/inventory_2:",
        },
        "graphs": {
            "label": "Analysis",
            "icon": ":material/monitoring:",
        },
        "ai": {
            "label": "A.I.",
            "icon": ":material/smart_toy:",
        },
    }

    def __init__(self):
        self.simulation_manager = SimulationFileManager()
        self.data_store = SalesDataStore()
        self.metrics = SalesMetrics()
        self.action_logger = AppActionLogger()
        self.finance_policy = CompanyFinancePolicy()
        self.historical_simulator = HistoricalSalesSimulator(
            self.simulation_manager,
            self.data_store,
        )
        self.pages = self.build_pages()

    def build_pages(self):
        """Wire shared services into each Streamlit page object."""

        page_args = (
            self.data_store,
            self.metrics,
            self.finance_policy,
            self.action_logger,
        )
        return {
            "calculator": CalculatorPage(
                *page_args,
                self.simulation_manager,
                self.historical_simulator,
            ),
            "inventory": InventoryPage(*page_args),
            "graphs": AnalysisPage(*page_args),
            "ai": AIPage(*page_args),
        }

    def run(self):
        st.set_page_config(page_title="Sales Calculator", layout="wide")
        st.markdown(AppStyles.STREAMLIT, unsafe_allow_html=True)
        section = self.show_section_tabs()
        self.pages[section].show()

    def show_section_tabs(self):
        if "section" not in st.session_state:
            st.session_state.section = "calculator"

        with st.sidebar:
            for item_section, item in self.nav_items.items():
                self.show_tab_button(item_section, item)

        return st.session_state.section

    @staticmethod
    def set_section(section):
        st.session_state.section = section

    def show_tab_button(self, section, item):
        """Render one sidebar tab with native Streamlit button icons."""

        button_type = "secondary"
        if st.session_state.section == section:
            button_type = "primary"

        st.button(
            item["label"],
            key=f"{section}_nav_tab",
            on_click=self.set_section,
            args=(section,),
            icon=item["icon"],
            type=button_type,
            width="stretch",
        )
