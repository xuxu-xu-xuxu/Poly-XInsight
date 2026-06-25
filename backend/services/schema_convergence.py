from backend.llm import get_llm_client
from backend.models.database import get_db, EntitySchema, EntitySynonym
from sqlalchemy import select
import json

CONVERGENCE_PROMPT = """你是材料科学术语专家。以下是从不同论文中提取的实体类型列表。
请识别含义相同但表述不同的类型，将它们合并为规范名称。

输入类型列表:
{type_list}

输出JSON:
{{
  "mappings": [
    {{"canonical": "规范名称", "variants": ["变体1", "变体2"]}}
  ]
}}

如果所有类型含义都不同不需要合并，返回空mappings数组。"""


async def run_schema_convergence() -> dict:
    async for db in get_db():
        result = await db.execute(select(EntitySchema.schema_json))
        schemas = [row[0] for row in result.fetchall()]
        break

    all_types = set()
    for s in schemas:
        for ent in s.get("entities", []):
            all_types.add(ent["type"])

    if len(all_types) < 2:
        return {"mapped": 0}

    llm = get_llm_client()
    prompt = CONVERGENCE_PROMPT.format(type_list=json.dumps(list(all_types), ensure_ascii=False))
    response = await llm.chat([{"role": "user", "content": prompt}])
    response = response.strip()
    if response.startswith("```json"):
        response = response[7:]
    if response.endswith("```"):
        response = response[:-3]
    mappings = json.loads(response)

    async for db in get_db():
        for m in mappings.get("mappings", []):
            canonical = m["canonical"]
            for variant in m["variants"]:
                db.add(EntitySynonym(canonical=canonical, variant=variant))
        await db.commit()
        break

    mapped_count = sum(len(m["variants"]) for m in mappings.get("mappings", []))
    return {"mapped": mapped_count}
