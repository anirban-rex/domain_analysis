from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from domain_decomposer.candidate_domains import build_candidate_domains
from domain_decomposer.cohesion_graph import build_graph
from domain_decomposer.java_source_parser import parse
from domain_decomposer.pipeline import run
from domain_decomposer.schemas import Facts


class CandidateDomainTests(unittest.TestCase):
    def _facts(self) -> Facts:
        return Facts.from_json({
            "nodes": [
                {"id": "shop.order.OrderService", "fqcn": "shop.order.OrderService", "package": "shop.order", "role": "service"},
                {"id": "shop.order.OrderRepository", "fqcn": "shop.order.OrderRepository", "package": "shop.order", "role": "repository"},
                {"id": "shop.order.Order", "fqcn": "shop.order.Order", "package": "shop.order", "role": "entity"},
                {"id": "shop.payment.PaymentService", "fqcn": "shop.payment.PaymentService", "package": "shop.payment", "role": "service"},
            ],
            "references": [
                {"source": "shop.order.OrderService", "target": "shop.order.OrderRepository", "type": "method_call", "method": "save"},
                {"source": "shop.payment.PaymentService", "target": "shop.order.OrderService", "type": "method_call", "method": "placeOrder"},
            ],
            "foreign_keys": [
                {"source": "shop.order.OrderRepository", "target": "shop.order.Order", "type": "entity_access"},
            ],
            "transactions": [
                {"id": "order-tx", "participants": ["shop.order.OrderService", "shop.order.OrderRepository"]},
            ],
            "embeddings": {
                "shop.order.OrderService": [1.0, 0.0],
                "shop.order.OrderRepository": [0.95, 0.05],
                "shop.order.Order": [0.9, 0.1],
                "shop.payment.PaymentService": [0.0, 1.0],
            },
        })

    def test_java_parser_uses_service_annotations_as_roles(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            java_file = source_root / "src/main/java/shop/payment/PaymentProcessor.java"
            java_file.parent.mkdir(parents=True)
            java_file.write_text(
                "package shop.payment;\n@org.springframework.stereotype.Service\npublic class PaymentProcessor {}\n",
                encoding="utf-8",
            )
            payload = parse(source_root)
        node = payload["nodes"][0]
        self.assertEqual(node["role"], "service")
        self.assertIn("Service", node["attributes"]["annotations"])

    def test_graph_edges_retain_pairwise_signal_provenance(self) -> None:
        facts = self._facts()
        graph = build_graph(
            facts,
            facts.embeddings,
            nearest_neighbors=2,
            minimum_edge_weight=0.05,
            pairwise_signals={"git_cocommit": {("shop.order.OrderService", "shop.payment.PaymentService"): 1.0}},
        )
        edge = graph.edges["shop.order.OrderService", "shop.order.OrderRepository"]
        self.assertIn("reference", edge["signal_scores"])
        self.assertIn("workflow", edge["signal_scores"])
        self.assertTrue(any(item["signal"] == "reference" for item in edge["evidence"]))
        self.assertGreater(edge["weight"], 0.0)
        cross_domain_edge = graph.edges["shop.order.OrderService", "shop.payment.PaymentService"]
        self.assertIn("git_cocommit", cross_domain_edge["signal_scores"])

    def test_candidate_domains_follow_louvain_labels_and_mark_review(self) -> None:
        facts = self._facts()
        graph = build_graph(facts, facts.embeddings, nearest_neighbors=1, minimum_edge_weight=0.05)
        labels = {
            "shop.order.OrderService": 1,
            "shop.order.OrderRepository": 1,
            "shop.order.Order": 1,
            "shop.payment.PaymentService": 2,
        }
        domains = build_candidate_domains(facts, graph, labels)
        self.assertEqual({item["id"] for item in domains["domains"]}, {1, 2})
        order_domain = next(item for item in domains["domains"] if item["id"] == 1)
        self.assertEqual(order_domain["name"], "Order")
        self.assertEqual(set(order_domain["members"]), {"shop.order.OrderService", "shop.order.OrderRepository", "shop.order.Order"})
        payment_domain = next(item for item in domains["domains"] if item["id"] == 2)
        self.assertIn("shop.payment.PaymentService", payment_domain["anchor_names"])
        self.assertTrue(domains["cross_domain_dependencies"])
        combined_labels = {node_id: 1 for node_id in facts.nodes}
        combined = build_candidate_domains(facts, graph, combined_labels)
        self.assertTrue(combined["domains"][0]["review_required"])
        self.assertTrue(any("Multiple service anchors" in reason for reason in combined["domains"][0]["review_reasons"]))

    def test_pipeline_writes_reviewable_domains_to_results_and_html(self) -> None:
        facts_payload = {
            "nodes": [
                {"id": "shop.order.OrderService", "fqcn": "shop.order.OrderService", "package": "shop.order", "role": "service"},
                {"id": "shop.order.OrderRepository", "fqcn": "shop.order.OrderRepository", "package": "shop.order", "role": "repository"},
                {"id": "shop.order.Order", "fqcn": "shop.order.Order", "package": "shop.order", "role": "entity"},
                {"id": "shop.payment.PaymentService", "fqcn": "shop.payment.PaymentService", "package": "shop.payment", "role": "service"},
            ],
            "references": [
                {"source": "shop.order.OrderService", "target": "shop.order.OrderRepository", "type": "method_call"},
                {"source": "shop.payment.PaymentService", "target": "shop.order.OrderService", "type": "method_call", "method": "placeOrder"},
            ],
            "foreign_keys": [{"source": "shop.order.OrderRepository", "target": "shop.order.Order"}],
            "transactions": [{"id": "order-tx", "participants": ["shop.order.OrderService", "shop.order.OrderRepository"]}],
            "embeddings": {
                "shop.order.OrderService": [1.0, 0.0],
                "shop.order.OrderRepository": [0.95, 0.05],
                "shop.order.Order": [0.9, 0.1],
                "shop.payment.PaymentService": [0.0, 1.0],
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "facts.json"
            output = root / "report"
            source.write_text(json.dumps(facts_payload), encoding="utf-8")
            report_path = run(str(source), str(output), nearest_neighbors=2, min_edge_weight=0.05)
            results = json.loads((output / "results.json").read_text(encoding="utf-8"))
            report = report_path.read_text(encoding="utf-8")
        self.assertIn("candidate_domains", results)
        assigned = {member for domain in results["candidate_domains"]["domains"] for member in domain["members"]}
        self.assertEqual(assigned, {node["id"] for node in facts_payload["nodes"]})
        self.assertIn("Candidate domains for review", report)
        self.assertIn("shop.order.OrderService", report)
        self.assertIn("Direct dependencies crossing candidate boundaries", report)


if __name__ == "__main__":
    unittest.main()
