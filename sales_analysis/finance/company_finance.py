class CompanyFinancePolicy:
    tax_rate = 0.20
    average_profit_margin = 50.0
    average_mom_growth = 5.0
    staff_hourly_wage = 22.0
    staff_count = 100
    monthly_health_insurance_per_staff = 300.0
    full_time_hours_per_week = 40
    weeks_per_year = 52
    months_per_year = 12

    def monthly_staff_payroll(self):
        yearly_payroll = (
            self.staff_hourly_wage
            * self.staff_count
            * self.full_time_hours_per_week
            * self.weeks_per_year
        )
        return yearly_payroll / self.months_per_year

    def monthly_health_insurance(self):
        return self.staff_count * self.monthly_health_insurance_per_staff

    def tax_amount(self, taxable_pay):
        if taxable_pay <= 0:
            return 0.0

        return taxable_pay * self.tax_rate

    def financial_summary(self, revenue, shipping_costs, month_count=1):
        """Calculate company-level deductions and net income for a period."""

        staff_payroll = self.monthly_staff_payroll() * month_count
        health_insurance = self.monthly_health_insurance() * month_count
        operating_expenses = staff_payroll + health_insurance
        break_even_margin = operating_expenses + shipping_costs
        gross_profit = revenue - shipping_costs
        taxable_pay = gross_profit - operating_expenses
        taxes = self.tax_amount(taxable_pay)

        return {
            "gross_profit": gross_profit,
            "staff_payroll": staff_payroll,
            "health_insurance": health_insurance,
            "operating_expenses": operating_expenses,
            "break_even_margin": break_even_margin,
            "taxes": taxes,
            "net_income": taxable_pay - taxes,
        }
