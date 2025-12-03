
from typing import List, Dict, Any, Optional
from ..views import (
    EnhancedDOMTreeNode,
    SimplifiedNode,
    SerializedDOMState,
    NodeType
)
class DOMTreeSerializer:
    def __init__(self, root_node: EnhancedDOMTreeNode):
        self.root_node = root_node
        self.selector_map = {}
        self.interactive_counter = 1

    def serialize(self) -> SerializedDOMState:
        simplified_tree = self._create_simplified_tree(self.root_node)
        self._assign_interactive_indices(simplified_tree)
        return SerializedDOMState(_root=simplified_tree, selector_map=self.selector_map)

    def _create_simplified_tree(self, node: EnhancedDOMTreeNode) -> Optional[SimplifiedNode]:
        if node.node_type == NodeType.DOCUMENT_NODE:
            children = []
            for child in node.children_and_shadow_roots:
                simplified_child = self._create_simplified_tree(child)
                if simplified_child:
                    children.append(simplified_child)
            return SimplifiedNode(original_node=node, children=children)

        if node.node_type == NodeType.ELEMENT_NODE:
            # Basic visibility check (placeholder)
            is_visible = True # node.is_visible 
            
            # Filter out non-visual tags
            if node.tag_name in ['script', 'style', 'noscript', 'meta', 'head', 'link', 'title']:
                return None

            # Interactive check (placeholder - check tag/role)
            is_interactive = self._is_interactive(node)

            children = []
            for child in node.children_and_shadow_roots:
                simplified_child = self._create_simplified_tree(child)
                if simplified_child:
                    children.append(simplified_child)
            
            if is_visible or children:
                return SimplifiedNode(original_node=node, children=children, is_interactive=is_interactive)

        if node.node_type == NodeType.TEXT_NODE:
            if node.node_value and node.node_value.strip():
                return SimplifiedNode(original_node=node, children=[])

        return None

    def _is_interactive(self, node: EnhancedDOMTreeNode) -> bool:
        # Simplified interactive check
        tag = node.tag_name
        if tag in ['a', 'button', 'input', 'select', 'textarea']:
            return True
        if node.attributes.get('role') in ['button', 'link', 'checkbox', 'radio', 'tab', 'menuitem', 'option']:
            return True
        if 'onclick' in node.attributes:
            return True
        return False

    def _assign_interactive_indices(self, node: Optional[SimplifiedNode]):
        if not node:
            return

        if node.is_interactive:
            node.original_node.node_id = self.interactive_counter # Use this as index for now
            self.selector_map[self.interactive_counter] = node.original_node
            self.interactive_counter += 1

        for child in node.children:
            self._assign_interactive_indices(child)

    @staticmethod
    def tree_to_string(node: SimplifiedNode, depth: int = 0) -> str:
        lines = []
        indent = "  " * depth
        
        if node.original_node.node_type == NodeType.DOCUMENT_NODE:
            for child in node.children:
                lines.append(DOMTreeSerializer.tree_to_string(child, depth))
        elif node.original_node.node_type == NodeType.TEXT_NODE:
            lines.append(f"{indent}{node.original_node.node_value.strip()}")
        elif node.original_node.node_type == NodeType.ELEMENT_NODE:
            tag = node.original_node.tag_name
            attrs = []
            for k, v in node.original_node.attributes.items():
                attrs.append(f'{k}="{v}"')
            attr_str = " ".join(attrs)
            
            prefix = ""
            if node.is_interactive:
                # Find the index from the node_id (which we set to the counter)
                index = node.original_node.node_id
                prefix = f"[i_{index}] "
            
            lines.append(f"{indent}{prefix}<{tag} {attr_str}>")
            
            for child in node.children:
                lines.append(DOMTreeSerializer.tree_to_string(child, depth + 1))
                
            lines.append(f"{indent}</{tag}>")
            
        return "\n".join(lines)
