import streamlit as st
from models.entities import TaskItem, ResourceItem, ReferenceItem, ProjectItem


def render_item(item: ProjectItem, on_complete=None, on_delete=None):
    """
    Polymorphic Renderer: Dispatches to specific render functions based on item type.
    """
    col_main, col_meta = st.columns([4, 1])

    # 1. Render Content based on Type
    if isinstance(item, TaskItem):
        _render_task(col_main, item, on_complete)
    elif isinstance(item, ResourceItem):
        _render_resource(col_main, item, on_complete)
    elif isinstance(item, ReferenceItem):
        _render_reference(col_main, item)

    # 2. Render Metadata (Right Column)
    with col_meta:
        # Simple date display
        st.caption(item.created_at.strftime("%m-%d"))


def _render_task(col, item: TaskItem, on_complete):
    # Task Checkbox
    is_checked = col.checkbox(
        item.name,
        value=item.is_completed,
        key=f"task_{item.id}"
    )

    # Handle completion callback if provided
    if is_checked != item.is_completed and on_complete:
        on_complete(item.id)
        st.rerun()

    # Metadata line
    meta_parts = []
    if item.tags:
        meta_parts.append(f"🏷️ {', '.join(item.tags)}")
    if item.duration and item.duration != "unknown":
        meta_parts.append(f"⏱️ {item.duration}")

    if meta_parts:
        col.caption(" | ".join(meta_parts))


def _render_resource(col, item: ResourceItem, on_complete):
    # Resource Checkbox (Acquired status)
    is_checked = col.checkbox(
        f"{item.name}",
        value=item.is_acquired,
        key=f"res_{item.id}"
    )

    if is_checked != item.is_acquired and on_complete:
        on_complete(item.id)
        st.rerun()

    col.caption(f"🛒 {item.store}")


def _render_reference(col, item: ReferenceItem):
    col.markdown(f"**📄 {item.name}**")
    if item.content:
        if item.content.startswith("http"):
            col.link_button("Open Link", item.content)
        else:
            col.caption(item.content)