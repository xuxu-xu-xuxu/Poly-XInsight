from backend.llm import get_llm_client
from backend.models.database import get_db, Entity, EntitySchema
import json
import os

SCHEMA_DISCOVERY_PROMPT = """你是一个材料科学文献分析专家。阅读以下论文内容，识别这篇论文涉及的所有实体类型和关系类型。

输出严格的JSON格式（不要加任何解释）:
{{
  "entities": [
    {{"type": "实体类型名", "attrs": ["属性1", "属性2"]}}
  ],
  "relations": ["实体A--关系名→实体B"]
}}

注意:
- 实体类型根据论文实际内容动态确定
- 属性要具体到这篇论文提到的信息维度
- 关系描述实体之间的关联

论文内容:
{paper_text}"""

EXTRACT_INSTANCES_PROMPT = """根据以下Schema，从论文中提取所有实体实例。

Schema:
{schema_json}

论文内容:
{paper_text}

输出严格JSON数组:
[
  {{"entity_type": "类型名", "attributes": {{"属性1": "值1"}}, "source_span": "§章节或段落位置"}}
]

只输出JSON，不要加任何解释。如果某类实体没有实例，对应的数组为空。"""


def _clean_json_response(response: str) -> str:
    response = response.strip()
    if response.startswith("```json"):
        response = response[7:]
    if response.startswith("```"):
        response = response[3:]
    if response.endswith("```"):
        response = response[:-3]
    return response.strip()


async def discover_schema(paper_text: str) -> dict:
    llm = get_llm_client()
    prompt = SCHEMA_DISCOVERY_PROMPT.format(paper_text=paper_text[:8000])
    response = await llm.chat([{"role": "user", "content": prompt}])
    return json.loads(_clean_json_response(response))


async def extract_instances(paper_text: str, schema: dict) -> list[dict]:
    llm = get_llm_client()
    prompt = EXTRACT_INSTANCES_PROMPT.format(
        schema_json=json.dumps(schema, ensure_ascii=False),
        paper_text=paper_text[:8000]
    )
    response = await llm.chat([{"role": "user", "content": prompt}])
    return json.loads(_clean_json_response(response))


async def run_extraction(paper_id: str, paper_text: str) -> dict:
    schema = await discover_schema(paper_text)
    os.makedirs("schemas", exist_ok=True)
    with open(f"schemas/{paper_id}_schema.json", "w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False)

    instances = await extract_instances(paper_text, schema)

    async for db in get_db():
        db.add(EntitySchema(paper_id=paper_id, schema_json=schema))
        for inst in instances:
            db.add(Entity(
                paper_id=paper_id,
                entity_type=inst["entity_type"],
                attributes=inst.get("attributes", {}),
                source_span=inst.get("source_span", ""),
            ))
        await db.commit()
        break

    return {"paper_id": paper_id, "schema": schema, "instance_count": len(instances)}
