import streamlit as st
from models.entities import TaskItem, ResourceItem, ReferenceItem, ProjectItem
from views.common import get_logger

logger = get_logger("Components")


def render_item(item: ProjectItem, on_complete=None, on_delete=None):
    """
    Polymorphic Renderer: Dispatches to specific render functions based on item type.
    """
    # LOGGING: Check what we are receiving
    # logger.debug(f"render_item called for: {item.name} (ID: {item.id}, Type: {type(item).__name__})")

    # LAYOUT FIX: Removed st.container(), used explicit columns
    col_main, col_meta = st.columns([0.85, 0.15])

    # ROBUST TYPE CHECKING: Use 'kind' string instead of isinstance
    # This handles Streamlit reloads where class definitions might drift
    kind = getattr(item, 'kind', None)

    if kind == 'task':
        _render_task(col_main, item, on_complete)
    elif kind == 'resource':
        _render_resource(col_main, item, on_complete)
    elif kind == 'reference':
        _render_reference(col_main, item)
    else:
        # Fallback logging
        logger.error(f"Unknown item type: {type(item)} - Kind: {kind}")
        col_main.error(f"Unknown item type: {item}")

    # 2. Render Metadata (Right Column)
    with col_meta:
        st.caption(item.created_at.strftime("%m-%d"))


def _render_task(col, item: TaskItem, on_complete):
    key = f"task_{item.id}"

    with col:
        # Using checkbox with label (hidden visibility) to ensure accessibility and layout
        is_checked = st.checkbox(
            item.name,
            value=item.is_completed,
            key=key,
            # label_visibility="collapsed"
        )

        # Render metadata line below checkbox
        meta_parts = []
        if item.tags:
            meta_parts.append(f"🏷️ {', '.join(item.tags)}")
        if item.duration and item.duration != "unknown":
            meta_parts.append(f"⏱️ {item.duration}")

        if meta_parts:
            st.caption(" | ".join(meta_parts))

    if is_checked != item.is_completed and on_complete:
        logger.info(f"Toggling completion for task: {item.name}")
        on_complete(item.id)
        st.rerun()


def _render_resource(col, item: ResourceItem, on_complete):
    key = f"res_{item.id}"
    with col:
        is_checked = st.checkbox(
            f"{item.name}",
            value=item.is_acquired,
            key=key
        )
        st.caption(f"🛒 {item.store}")

    if is_checked != item.is_acquired and on_complete:
        logger.info(f"Toggling acquisition for resource: {item.name}")
        on_complete(item.id)
        st.rerun()


def _render_reference(col, item: ReferenceItem):
    with col:
        st.markdown(f"**📄 {item.name}**")
        if item.content:
            if item.content.startswith("http"):
                st.link_button("Open Link", item.content)
            else:
                st.caption(item.content)