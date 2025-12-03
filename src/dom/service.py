import asyncio
import logging
from typing import List, Dict, Any, Optional
from playwright.async_api import Page, CDPSession
from .views import (
    EnhancedDOMTreeNode,
    EnhancedSnapshotNode,
    EnhancedAXNode,
    EnhancedAXProperty,
    DOMRect,
    NodeType,
    SerializedDOMState
)
from .serializer.service import DOMTreeSerializer

logger = logging.getLogger(__name__)

class CDPDomService:
    def __init__(self, page: Page):
        self.page = page
        self.cdp_session: Optional[CDPSession] = None
        self.last_snapshot: Optional[SerializedDOMState] = None

    async def _ensure_cdp_session(self):
        if not self.cdp_session:
            self.cdp_session = await self.page.context.new_cdp_session(self.page)

    async def get_snapshot(self) -> SerializedDOMState:
        await self._ensure_cdp_session()
        
        # 1. Get DOM Tree
        dom_tree = await self.cdp_session.send("DOM.getDocument", {"depth": -1, "pierce": True})
        
        # 2. Get Layout Metrics (for viewport)
        layout_metrics = await self.cdp_session.send("Page.getLayoutMetrics")
        
        # 3. Get Accessibility Tree
        ax_tree = await self.cdp_session.send("Accessibility.getFullAXTree")
        
        # 4. Capture Snapshot (computed styles, bounds, etc.)
        snapshot = await self.cdp_session.send("DOMSnapshot.captureSnapshot", {
            "computedStyles": ["display", "visibility", "opacity", "overflow", "overflow-x", "overflow-y"],
            "includePaintOrder": True,
            "includeDOMRects": True
        })

        # Process and merge data
        root_node = self._build_enhanced_tree(dom_tree['root'], ax_tree['nodes'], snapshot)
        
        # Serialize
        serializer = DOMTreeSerializer(root_node)
        # Serialize
        serializer = DOMTreeSerializer(root_node)
        self.last_snapshot = serializer.serialize()
        return self.last_snapshot

    async def click_element(self, index: int):
        if not self.last_snapshot or index not in self.last_snapshot.selector_map:
            raise ValueError(f"Element with index {index} not found in current snapshot")
        
        node = self.last_snapshot.selector_map[index]
        await self._ensure_cdp_session()
        
        # Use DOM.resolveNode to get a remote object ID, then Input.dispatchMouseEvent
        # Or simpler: use DOM.scrollIntoViewIfNeeded and Input.dispatchMouseEvent
        
        # 1. Resolve node to get objectId
        resolved = await self.cdp_session.send("DOM.resolveNode", {"backendNodeId": node.backend_node_id})
        object_id = resolved['object']['objectId']
        
        # 2. Scroll into view
        await self.cdp_session.send("DOM.scrollIntoViewIfNeeded", {"objectId": object_id})
        
        # 3. Get box model to find center
        box = await self.cdp_session.send("DOM.getBoxModel", {"backendNodeId": node.backend_node_id})
        content = box['model']['content'] # [x1, y1, x2, y2, x3, y3, x4, y4]
        center_x = (content[0] + content[4]) / 2
        center_y = (content[1] + content[5]) / 2
        
        # 4. Dispatch click events
        await self.cdp_session.send("Input.dispatchMouseEvent", {
            "type": "mousePressed", "x": center_x, "y": center_y, "button": "left", "clickCount": 1
        })
        await self.cdp_session.send("Input.dispatchMouseEvent", {
            "type": "mouseReleased", "x": center_x, "y": center_y, "button": "left", "clickCount": 1
        })

    def get_element_by_index(self, index: int, level: int = 0) -> Dict[str, Any]:
        if not self.last_snapshot or index not in self.last_snapshot.selector_map:
            raise ValueError(f"Element with index {index} not found in current snapshot")
        
        node = self.last_snapshot.selector_map[index]
        
        # Traverse up if level > 0
        current_node = node
        for _ in range(level):
            if current_node.parent_node:
                current_node = current_node.parent_node
            else:
                break
        
        return {
            "tag_name": current_node.tag_name,
            "text_content": current_node.get_all_children_text(),
            "attributes": current_node.attributes,
            "children_ids": [] # Placeholder
        }

    def _build_enhanced_tree(self, dom_node: Dict, ax_nodes: List[Dict], snapshot: Dict) -> EnhancedDOMTreeNode:
        # Create lookups
        ax_lookup = {node['backendDOMNodeId']: node for node in ax_nodes if 'backendDOMNodeId' in node}
        
        # Helper to recursively build tree
        def build_node(node_data: Dict, parent: Optional[EnhancedDOMTreeNode] = None) -> EnhancedDOMTreeNode:
            backend_id = node_data['backendNodeId']
            
            # AX Node
            ax_data = ax_lookup.get(backend_id)
            enhanced_ax = None
            if ax_data:
                enhanced_ax = EnhancedAXNode(
                    ax_node_id=ax_data['nodeId'],
                    ignored=ax_data['ignored'],
                    role=ax_data.get('role', {}).get('value'),
                    name=ax_data.get('name', {}).get('value'),
                    description=ax_data.get('description', {}).get('value'),
                    properties=[EnhancedAXProperty(p['name'], p.get('value', {}).get('value')) for p in ax_data.get('properties', [])],
                    child_ids=ax_data.get('childIds')
                )

            # Snapshot Node (Simplified mapping for now - requires complex index mapping in real browser-use)
            # In a real implementation, we need to map snapshot arrays to nodes. 
            # For this MVP, we might skip detailed snapshot mapping if it's too complex to reverse engineer quickly,
            # but browser-use relies on it for visibility.
            # Let's try to do a basic mapping if possible, or assume visibility based on AX/DOM for now.
            # browser-use uses `build_snapshot_lookup` which is complex.
            # For now, we'll create a placeholder EnhancedSnapshotNode.
            enhanced_snapshot = EnhancedSnapshotNode(
                is_clickable=True, # Placeholder
                cursor_style="pointer",
                bounds=None, # Need to map from snapshot['documents'][0]['layout']['nodeIndex']...
                clientRects=None,
                scrollRects=None,
                computed_styles={},
                paint_order=0,
                stacking_contexts=0
            )

            enhanced_node = EnhancedDOMTreeNode(
                node_id=node_data['nodeId'],
                backend_node_id=backend_id,
                node_type=NodeType(node_data['nodeType']),
                node_name=node_data['nodeName'],
                node_value=node_data['nodeValue'],
                attributes={node_data['attributes'][i]: node_data['attributes'][i+1] for i in range(0, len(node_data.get('attributes', [])), 2)},
                is_scrollable=False, # Placeholder
                is_visible=True, # Placeholder
                absolute_position=None,
                target_id="page",
                frame_id=node_data.get('frameId'),
                session_id=None,
                content_document=None,
                shadow_root_type=node_data.get('shadowRootType'),
                shadow_roots=[],
                parent_node=parent,
                children_nodes=[],
                ax_node=enhanced_ax,
                snapshot_node=enhanced_snapshot
            )

            # Process children
            if 'children' in node_data:
                for child_data in node_data['children']:
                    child_node = build_node(child_data, enhanced_node)
                    enhanced_node.children_nodes.append(child_node)
            
            # Process shadow roots
            if 'shadowRoots' in node_data:
                for shadow_data in node_data['shadowRoots']:
                    shadow_node = build_node(shadow_data, enhanced_node)
                    enhanced_node.shadow_roots.append(shadow_node)
            
            # Process content document (iframe)
            if 'contentDocument' in node_data:
                enhanced_node.content_document = build_node(node_data['contentDocument'], enhanced_node)

            return enhanced_node

        return build_node(dom_node)
