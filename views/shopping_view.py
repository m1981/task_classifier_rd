import streamlit as st
from services.repository import ExecutionService

def render_shopping_view(service: ExecutionService):
    st.title("🛒 Shopping Run")

    # Get the pivoted data
    shopping_data = service.get_aggregated_shopping_list()

    if not shopping_data:
        st.info("Nothing to buy! Good job.")
        return

    # Render a section for each Store
    for store_name, items in shopping_data.items():
        with st.expander(f"📍 {store_name} ({len(items)} items)", expanded=True):

            for resource, project_name in items:
                col1, col2 = st.columns([4, 1])

                # The Checkbox
                is_checked = col1.checkbox(
                    f"{resource.name} ({project_name})",
                    value=resource.is_acquired,
                    key=f"shop_{resource.id}"
                )

                # If checked, update the underlying data immediately
                if is_checked != resource.is_acquired:
                    service.toggle_resource_status(resource.id, is_checked)
                    st.rerun()

                # Optional: Link button if it exists
                if resource.link:
                    col2.link_button("🔗", resource.link)