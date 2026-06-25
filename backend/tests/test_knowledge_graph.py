from backend.services.topic_navigation import build_topic_graph


def test_build_topic_graph_omits_domain_nodes_when_disabled():
    cards = [
        {
            "id": "topic:llzo",
            "label": "LLZO densification",
            "domain_id": "solid-state",
            "paper_count": 1,
            "papers": [{"id": "paper-1", "title": "Ta-doped LLZO densification", "year": 2024, "journal": None}],
            "highlights": {
                "materials": [{"label": "LLZO", "count": 1}],
                "methods": [{"label": "sintering", "count": 1}],
                "problems": [{"label": "densification/porosity", "count": 1}],
                "properties": [{"label": "relative density", "count": 1}],
            },
        }
    ]

    graph = build_topic_graph(cards, include_domains=False)

    assert all(node["type"] != "domain" for node in graph["nodes"])
    assert all(edge["type"] != "domain_topic" for edge in graph["edges"])
