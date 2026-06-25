from backend.services.topic_navigation import (
    build_topic_cards,
    build_topic_graph,
    infer_problem_signals,
)


def test_infer_problem_signals_normalizes_research_bottlenecks():
    text = (
        "The sulfide electrolyte still suffers from moisture sensitivity and H2S release. "
        "Its interfacial resistance against lithium metal also remains high."
    )

    problems = infer_problem_signals(text)

    assert "air/moisture sensitivity" in problems
    assert "interface instability" in problems
    assert "anode compatibility" in problems


def test_build_topic_cards_groups_clustered_papers_and_ranks_signals():
    papers = [
        {
            "id": "paper-1",
            "title": "Interface coating for sulfide electrolytes",
            "year": 2024,
            "journal": "Energy Storage Materials",
            "domain_id": "solid-state",
            "topic_label": "Sulfide interface engineering",
            "signals": {
                "materials": ["Li6PS5Cl", "LiNbO3"],
                "methods": ["coating", "EIS"],
                "problems": ["interface instability", "air/moisture sensitivity"],
                "properties": ["ionic conductivity", "cycle stability"],
            },
        },
        {
            "id": "paper-2",
            "title": "Moisture protection route for argyrodite SSEs",
            "year": 2023,
            "journal": "Joule",
            "domain_id": "solid-state",
            "topic_label": "Sulfide interface engineering",
            "signals": {
                "materials": ["Li6PS5Cl"],
                "methods": ["coating", "surface treatment"],
                "problems": ["air/moisture sensitivity"],
                "properties": ["air stability"],
            },
        },
        {
            "id": "paper-3",
            "title": "Ta-doped LLZO densification",
            "year": 2022,
            "journal": "Advanced Energy Materials",
            "domain_id": "solid-state",
            "topic_label": "LLZO densification",
            "signals": {
                "materials": ["LLZO"],
                "methods": ["Ta doping", "sintering"],
                "problems": ["densification/porosity"],
                "properties": ["relative density"],
            },
        },
    ]

    cards = build_topic_cards(papers, max_topics=6, papers_per_topic=3)

    assert [card["label"] for card in cards] == [
        "Sulfide interface engineering",
        "LLZO densification",
    ]
    assert cards[0]["paper_count"] == 2
    assert cards[0]["is_fallback_topic"] is False
    assert cards[0]["highlights"]["materials"][0]["label"] == "Li6PS5Cl"
    assert cards[0]["highlights"]["methods"][0]["label"] == "coating"
    assert cards[0]["highlights"]["problems"][0]["label"] == "air/moisture sensitivity"
    assert cards[0]["papers"][0]["id"] == "paper-1"


def test_build_topic_cards_marks_fallback_topics():
    cards = build_topic_cards(
        [
            {
                "id": "paper-x",
                "title": "General paper",
                "year": 2025,
                "journal": None,
                "domain_id": "solid-state",
                "topic_label": "Solid-state literature",
                "signals": {"materials": [], "methods": [], "problems": [], "properties": []},
                "is_fallback_topic": True,
            }
        ],
        max_topics=4,
        papers_per_topic=2,
    )

    assert cards[0]["label"] == "Solid-state literature"
    assert cards[0]["is_fallback_topic"] is True


def test_build_topic_graph_emits_topic_and_signal_nodes():
    cards = [
        {
            "id": "topic:sulfide-interface-engineering",
            "label": "Sulfide interface engineering",
            "domain_id": "solid-state",
            "paper_count": 2,
            "papers": [
                {"id": "paper-1", "title": "Interface coating for sulfide electrolytes", "year": 2024},
                {"id": "paper-2", "title": "Moisture protection route for argyrodite SSEs", "year": 2023},
            ],
            "highlights": {
                "materials": [{"label": "Li6PS5Cl", "count": 2}],
                "methods": [{"label": "coating", "count": 2}],
                "problems": [{"label": "air/moisture sensitivity", "count": 2}],
                "properties": [{"label": "ionic conductivity", "count": 1}],
            },
        }
    ]

    graph = build_topic_graph(cards, include_domains=True)

    node_types = {(node["id"], node["type"]) for node in graph["nodes"]}
    edge_types = {(edge["source"], edge["target"], edge["type"]) for edge in graph["edges"]}

    assert ("domain:solid-state", "domain") in node_types
    assert ("topic:sulfide-interface-engineering", "topic") in node_types
    assert ("paper:paper-1", "paper") in node_types
    assert ("material:li6ps5cl", "material") in node_types
    assert ("method:coating", "method") in node_types
    assert ("problem:air-moisture-sensitivity", "problem") in node_types
    assert ("property:ionic-conductivity", "property") in node_types
    assert (
        "topic:sulfide-interface-engineering",
        "paper:paper-1",
        "topic_paper",
    ) in edge_types
    assert (
        "topic:sulfide-interface-engineering",
        "material:li6ps5cl",
        "topic_signal",
    ) in edge_types
