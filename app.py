import streamlit as st
from pipeline.gift_finder import run

st.set_page_config(
    page_title="Mumzworld Gift Finder",
    page_icon="🎁",
    layout="centered",
)

# Header
st.markdown("## 🎁 Mumzworld Gift Finder")
st.markdown("Describe the gift you're looking for in English or Arabic — we'll find the best match.")

# Example queries
st.markdown("**Try these:**")
examples = [
    "Thoughtful gift for a friend with a 6-month-old, under 200 AED",
    "Educational toy for a 2-year-old boy, budget 150 AED",
    "هدية لطفلة حديثة الولادة، الميزانية 300 درهم",
    "Something for a baby shower, under 50 AED",
    "Gift for a breastfeeding mom, under 100 AED",
]
cols = st.columns(2)
for i, ex in enumerate(examples):
    if cols[i % 2].button(ex, key=f"ex_{i}", use_container_width=True):
        st.session_state["query_input"] = ex

# Input
query = st.text_input(
    "Your request:",
    value=st.session_state.get("query_input", ""),
    placeholder="e.g. gift for a 6-month-old under 200 AED",
    key="query_input",
)

if st.button("Find Gifts 🎁", type="primary", use_container_width=True):
    if not query.strip():
        st.warning("Please enter a gift request.")
    else:
        with st.spinner("Finding the perfect gift..."):
            try:
                result = run(query)
            except Exception as e:
                st.error(f"Something went wrong: {e}")
                st.stop()

        # Show parsed intent
        with st.expander("🔍 Parsed Intent", expanded=False):
            intent = result.intent
            cols = st.columns(3)
            cols[0].metric("Child Age", f"{intent.child_age_months}m" if intent.child_age_months else "Not specified")
            cols[1].metric("Budget", f"{intent.budget_aed} AED" if intent.budget_aed else "Not specified")
            cols[2].metric("Occasion", intent.occasion or "Not specified")
            if intent.preferences:
                st.write("**Preferences:**", ", ".join(intent.preferences))
            if intent.is_for_mom:
                st.info("🤱 This gift is for the mother.")

        st.divider()

        # No match
        if not result.recommendations:
            st.warning(f"😔 {result.no_match_reason}")

        # Recommendations
        else:
            st.markdown(f"### Found {len(result.recommendations)} gift(s) for you")
            for i, rec in enumerate(result.recommendations):
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"#### {i+1}. {rec.name_en}")
                        st.markdown(f"*{rec.name_ar}*")
                    with col2:
                        st.metric("Price", f"{rec.price_aed} AED")
                        confidence_pct = int(rec.confidence * 100)
                        st.metric("Match", f"{confidence_pct}%")

                    st.markdown("**Why this gift?**")
                    tab_en, tab_ar = st.tabs(["🇬🇧 English", "🇦🇪 Arabic"])
                    with tab_en:
                        st.write(rec.reason_en)
                    with tab_ar:
                        st.markdown(
                            f"<div style='direction:rtl; text-align:right; font-size:1.1em'>{rec.reason_ar}</div>",
                            unsafe_allow_html=True,
                        )

                    badges = []
                    if rec.age_suitable:
                        badges.append("✅ Age appropriate")
                    if rec.within_budget:
                        badges.append("✅ Within budget")
                    st.markdown(" &nbsp;|&nbsp; ".join(badges))