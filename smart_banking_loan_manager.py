import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st


# ---------------------------------------------------------
# SMART BANKING LOAN & EMI MANAGEMENT SYSTEM
# Educational demo project. Not an official bank application.
# ---------------------------------------------------------

DB_NAME = "loan_records.db"


def create_database():
    """Create the SQLite database and loan records table."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS loan_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                loan_type TEXT NOT NULL,
                loan_amount REAL NOT NULL,
                annual_interest_rate REAL NOT NULL,
                tenure_years INTEGER NOT NULL,
                monthly_emi REAL NOT NULL,
                total_interest REAL NOT NULL,
                total_payment REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def calculate_emi(principal, annual_rate, tenure_years):
    """Calculate EMI for a fixed-rate, reducing-balance loan."""
    months = tenure_years * 12
    monthly_rate = annual_rate / (12 * 100)

    if monthly_rate == 0:
        return principal / months

    factor = (1 + monthly_rate) ** months
    emi = principal * monthly_rate * factor / (factor - 1)
    return emi


def get_loan_summary(principal, annual_rate, tenure_years):
    """Return EMI, total payment and total interest."""
    months = tenure_years * 12
    emi = calculate_emi(principal, annual_rate, tenure_years)
    total_payment = emi * months
    total_interest = total_payment - principal

    return {
        "emi": emi,
        "total_payment": total_payment,
        "total_interest": total_interest,
        "months": months,
    }


def build_amortization_schedule(principal, annual_rate, tenure_years):
    """Build an illustrative month-by-month repayment schedule."""
    months = tenure_years * 12
    monthly_rate = annual_rate / (12 * 100)
    emi = calculate_emi(principal, annual_rate, tenure_years)
    balance = float(principal)
    rows = []

    for month in range(1, months + 1):
        interest_component = balance * monthly_rate
        principal_component = emi - interest_component

        # Adjust the final instalment to clear rounding differences.
        if month == months or principal_component > balance:
            principal_component = balance
            payment = principal_component + interest_component
        else:
            payment = emi

        balance = max(0.0, balance - principal_component)

        rows.append(
            {
                "Month": month,
                "EMI (₹)": round(payment, 2),
                "Principal (₹)": round(principal_component, 2),
                "Interest (₹)": round(interest_component, 2),
                "Remaining Balance (₹)": round(balance, 2),
            }
        )

    return pd.DataFrame(rows)


def save_loan_record(
    customer_name,
    loan_type,
    principal,
    annual_rate,
    tenure_years,
    summary,
):
    """Save a calculation to the local SQLite database."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            """
            INSERT INTO loan_records (
                customer_name, loan_type, loan_amount,
                annual_interest_rate, tenure_years, monthly_emi,
                total_interest, total_payment, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                customer_name,
                loan_type,
                principal,
                annual_rate,
                tenure_years,
                summary["emi"],
                summary["total_interest"],
                summary["total_payment"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()


def load_loan_records():
    """Load saved calculations from SQLite."""
    with sqlite3.connect(DB_NAME) as conn:
        return pd.read_sql_query(
            "SELECT * FROM loan_records ORDER BY id DESC", conn
        )


def format_inr(amount):
    return f"₹{amount:,.2f}"


# ------------------------- PAGE SETUP -------------------------

st.set_page_config(
    page_title="Smart Banking Loan Manager",
    page_icon="🏦",
    layout="wide",
)

create_database()

st.title("🏦 Smart Banking Loan & EMI Management System")
st.caption(
    "A Python learning project for loan calculations, comparisons, "
    "repayment schedules and local record keeping."
)

st.info(
    "Educational demonstration only. The interest rate and results are "
    "illustrative. This application does not assess creditworthiness, "
    "approve loans, or represent ICICI Bank or any other bank."
)

calculator_tab, comparison_tab, records_tab = st.tabs(
    ["🧮 EMI Calculator", "📊 Loan Comparison", "🗂️ Saved Records"]
)


# ------------------------- EMI CALCULATOR -------------------------

with calculator_tab:
    st.subheader("Calculate a loan EMI")

    left, right = st.columns([1, 1])

    with left:
        customer_name = st.text_input(
            "Customer name (use sample details for demonstration)",
            placeholder="e.g. Demo Customer",
        )
        loan_type = st.selectbox(
            "Loan type",
            ["Personal Loan", "Education Loan", "Home Loan", "Vehicle Loan"],
        )
        principal = st.number_input(
            "Loan amount (₹)",
            min_value=1_000.0,
            max_value=10_00_00_000.0,
            value=5_00_000.0,
            step=10_000.0,
        )
        annual_rate = st.number_input(
            "Annual interest rate (%)",
            min_value=0.0,
            max_value=50.0,
            value=10.0,
            step=0.25,
        )
        tenure_years = st.number_input(
            "Loan tenure (years)",
            min_value=1,
            max_value=30,
            value=5,
            step=1,
        )

        calculate_clicked = st.button(
            "Calculate EMI", type="primary", use_container_width=True
        )

    with right:
        st.markdown("#### What this calculator considers")
        st.write(
            "- Fixed annual interest rate\n"
            "- Monthly reducing-balance calculation\n"
            "- Equal monthly instalments\n"
            "- Total repayment and total interest\n"
            "- Month-by-month illustrative repayment schedule"
        )
        st.warning(
            "Actual bank quotations may differ due to fees, taxes, "
            "rate changes, payment dates and lender-specific terms."
        )

    if calculate_clicked:
        if not customer_name.strip():
            st.error("Please enter a customer name.")
        elif principal <= 0 or annual_rate < 0 or tenure_years <= 0:
            st.error("Please enter valid positive loan details.")
        else:
            summary = get_loan_summary(
                principal, annual_rate, int(tenure_years)
            )
            st.session_state["last_calculation"] = {
                "customer_name": customer_name.strip(),
                "loan_type": loan_type,
                "principal": principal,
                "annual_rate": annual_rate,
                "tenure_years": int(tenure_years),
                "summary": summary,
            }

    if "last_calculation" in st.session_state:
        result = st.session_state["last_calculation"]
        summary = result["summary"]

        st.divider()
        st.subheader("Loan calculation result")

        metric1, metric2, metric3 = st.columns(3)
        metric1.metric("Monthly EMI", format_inr(summary["emi"]))
        metric2.metric("Total interest", format_inr(summary["total_interest"]))
        metric3.metric("Total repayment", format_inr(summary["total_payment"]))

        st.write(
            f"**Customer:** {result['customer_name']}  |  "
            f"**Loan:** {result['loan_type']}  |  "
            f"**Tenure:** {result['tenure_years']} years"
        )

        chart_data = pd.DataFrame(
            {
                "Component": ["Principal", "Total interest"],
                "Amount (₹)": [
                    result["principal"],
                    summary["total_interest"],
                ],
            }
        )
        st.bar_chart(chart_data.set_index("Component"))

        schedule = build_amortization_schedule(
            result["principal"],
            result["annual_rate"],
            result["tenure_years"],
        )
        st.markdown("#### Repayment schedule")
        st.dataframe(schedule, use_container_width=True, hide_index=True)

        if st.button("Save this calculation to records"):
            save_loan_record(
                result["customer_name"],
                result["loan_type"],
                result["principal"],
                result["annual_rate"],
                result["tenure_years"],
                summary,
            )
            st.success("Calculation saved in the local SQLite database.")


# ------------------------- LOAN COMPARISON -------------------------

with comparison_tab:
    st.subheader("Compare different loan tenures")
    st.write(
        "Compare monthly EMI and total interest for the same loan amount "
        "and annual interest rate."
    )

    c1, c2 = st.columns(2)
    with c1:
        compare_principal = st.number_input(
            "Comparison loan amount (₹)",
            min_value=1_000.0,
            value=5_00_000.0,
            step=10_000.0,
            key="compare_principal",
        )
    with c2:
        compare_rate = st.number_input(
            "Comparison annual interest rate (%)",
            min_value=0.0,
            max_value=50.0,
            value=10.0,
            step=0.25,
            key="compare_rate",
        )

    tenures = st.multiselect(
        "Choose loan durations",
        options=[1, 2, 3, 4, 5, 7, 10, 15, 20, 25, 30],
        default=[3, 5, 7],
    )

    if tenures:
        comparison_rows = []
        for years in sorted(tenures):
            summary = get_loan_summary(
                compare_principal, compare_rate, years
            )
            comparison_rows.append(
                {
                    "Tenure (years)": years,
                    "Monthly EMI (₹)": round(summary["emi"], 2),
                    "Total Interest (₹)": round(
                        summary["total_interest"], 2
                    ),
                    "Total Repayment (₹)": round(
                        summary["total_payment"], 2
                    ),
                }
            )

        comparison_df = pd.DataFrame(comparison_rows)
        st.dataframe(
            comparison_df, use_container_width=True, hide_index=True
        )
        st.markdown("#### Monthly EMI comparison")
        st.bar_chart(
            comparison_df.set_index("Tenure (years)")[
                ["Monthly EMI (₹)"]
            ]
        )
    else:
        st.warning("Select at least one loan duration to compare.")


# ------------------------- SAVED RECORDS -------------------------

with records_tab:
    st.subheader("Saved loan calculations")
    st.write(
        "Records are stored locally in the `loan_records.db` SQLite file "
        "on the computer running this application."
    )

    records = load_loan_records()

    if records.empty:
        st.info("No saved records yet. Calculate an EMI and save it first.")
    else:
        st.metric("Total saved calculations", len(records))
        st.dataframe(records, use_container_width=True, hide_index=True)

        csv_data = records.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download records as CSV",
            data=csv_data,
            file_name="loan_records.csv",
            mime="text/csv",
        )

st.divider()
st.caption(
    "Built with Python, Streamlit, Pandas and SQLite | "
    "Portfolio demonstration project"
)
