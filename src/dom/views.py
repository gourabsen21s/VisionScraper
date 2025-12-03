from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional, Dict
import hashlib

# Simplified types from cdp_use
class NodeType(int, Enum):
    ELEMENT_NODE = 1
    ATTRIBUTE_NODE = 2
    TEXT_NODE = 3
    CDATA_SECTION_NODE = 4
    ENTITY_REFERENCE_NODE = 5
    ENTITY_NODE = 6
    PROCESSING_INSTRUCTION_NODE = 7
    COMMENT_NODE = 8
    DOCUMENT_NODE = 9
    DOCUMENT_TYPE_NODE = 10
    DOCUMENT_FRAGMENT_NODE = 11
    NOTATION_NODE = 12

@dataclass
class DOMRect:
    x: float
    y: float
    width: float
    height: float

    def to_dict(self) -> dict[str, Any]:
        return {
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
        }

@dataclass
class EnhancedAXProperty:
    name: str
    value: Any

@dataclass
class EnhancedAXNode:
    ax_node_id: str
    ignored: bool
    role: Optional[str]
    name: Optional[str]
    description: Optional[str]
    properties: Optional[List[EnhancedAXProperty]]
    child_ids: Optional[List[str]]

@dataclass
class EnhancedSnapshotNode:
    is_clickable: Optional[bool]
    cursor_style: Optional[str]
    bounds: Optional[DOMRect]
    clientRects: Optional[DOMRect]
    scrollRects: Optional[DOMRect]
    computed_styles: Optional[Dict[str, str]]
    paint_order: Optional[int]
    stacking_contexts: Optional[int]

@dataclass
class EnhancedDOMTreeNode:
    node_id: int
    backend_node_id: int
    node_type: NodeType
    node_name: str
    node_value: str
    attributes: Dict[str, str]
    is_scrollable: Optional[bool]
    is_visible: Optional[bool]
    absolute_position: Optional[DOMRect]
    
    # Frames
    target_id: str
    frame_id: Optional[str]
    session_id: Optional[str]
    content_document: Optional['EnhancedDOMTreeNode']
    
    # Shadow DOM
    shadow_root_type: Optional[str]
    shadow_roots: Optional[List['EnhancedDOMTreeNode']]
    
    # Navigation
    parent_node: Optional['EnhancedDOMTreeNode']
    children_nodes: Optional[List['EnhancedDOMTreeNode']]
    
    # AX and Snapshot data
    ax_node: Optional[EnhancedAXNode]
    snapshot_node: Optional[EnhancedSnapshotNode]
    
    # Compound control child components
    _compound_children: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def children(self) -> List['EnhancedDOMTreeNode']:
        return self.children_nodes or []

    @property
    def children_and_shadow_roots(self) -> List['EnhancedDOMTreeNode']:
        children = list(self.children_nodes) if self.children_nodes else []
        if self.shadow_roots:
            children.extend(self.shadow_roots)
        return children

    @property
    def tag_name(self) -> str:
        return self.node_name.lower()

    def get_all_children_text(self, max_depth: int = -1) -> str:
        text_parts = []

        def collect_text(node: EnhancedDOMTreeNode, current_depth: int) -> None:
            if max_depth != -1 and current_depth > max_depth:
                return

            if node.node_type == NodeType.TEXT_NODE:
                text_parts.append(node.node_value)
            elif node.node_type == NodeType.ELEMENT_NODE:
                for child in node.children:
                    collect_text(child, current_depth + 1)

        collect_text(self, 0)
        return '\n'.join(text_parts).strip()

    @property
    def is_actually_scrollable(self) -> bool:
        if self.is_scrollable:
            return True
        
        if not self.snapshot_node:
            return False

        scroll_rects = self.snapshot_node.scrollRects
        client_rects = self.snapshot_node.clientRects

        if scroll_rects and client_rects:
            has_vertical_scroll = scroll_rects.height > client_rects.height + 1
            has_horizontal_scroll = scroll_rects.width > client_rects.width + 1

            if has_vertical_scroll or has_horizontal_scroll:
                if self.snapshot_node.computed_styles:
                    styles = self.snapshot_node.computed_styles
                    overflow = styles.get('overflow', 'visible').lower()
                    overflow_x = styles.get('overflow-x', overflow).lower()
                    overflow_y = styles.get('overflow-y', overflow).lower()

                    allows_scroll = (
                        overflow in ['auto', 'scroll', 'overlay']
                        or overflow_x in ['auto', 'scroll', 'overlay']
                        or overflow_y in ['auto', 'scroll', 'overlay']
                    )
                    return allows_scroll
                else:
                    scrollable_tags = {'div', 'main', 'section', 'article', 'aside', 'body', 'html'}
                    return self.tag_name.lower() in scrollable_tags
        return False

    @property
    def should_show_scroll_info(self) -> bool:
        if self.tag_name.lower() == 'iframe':
            return True
        if not (self.is_scrollable or self.is_actually_scrollable):
            return False
        if self.tag_name.lower() in {'body', 'html'}:
            return True
        if self.parent_node and (self.parent_node.is_scrollable or self.parent_node.is_actually_scrollable):
            return False
        return True

    def get_scroll_info_text(self) -> str:
        # Simplified for now
        if self.should_show_scroll_info:
            return "scrollable"
        return ""

@dataclass
class SimplifiedNode:
    original_node: EnhancedDOMTreeNode
    children: List['SimplifiedNode']
    should_display: bool = True
    is_interactive: bool = False
    is_new: bool = False
    ignored_by_paint_order: bool = False
    excluded_by_parent: bool = False
    is_shadow_host: bool = False
    is_compound_component: bool = False

@dataclass
class SerializedDOMState:
    _root: SimplifiedNode
    selector_map: Dict[int, EnhancedDOMTreeNode]

@dataclass
class DOMInteractedElement:
    index: int
