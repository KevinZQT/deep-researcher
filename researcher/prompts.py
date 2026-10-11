query_generate_instructions = """

Your goal is to generate sophisticated and diverse web search queries. These queries are intended for an advanced automated web research tool capable of analyzing complex results, following links, and synthesizing information.

Instructions:
- Always prefer a single search query, only add another query if the original question requests multiple aspects or elements and one query is not enough.
- Each query should focus on one specific aspect of the original question.
- Don't produce more than {number_queries} queries.
- Queries should be diverse, if the topic is broad, generate more than 1 query.
- Don't generate multiple similar queries, 1 is enough.
- Query should ensure that the most current information is gathered. The current date is {current_date}.

Format: 
- Format your response as a JSON object with ALL two of these exact keys:
   - "rationale": Brief explanation of why these queries are relevant
   - "query": A list of search queries

Example:

Topic: What revenue grew more last year apple stock or the number of people buying an iphone
```json
{{
    "rationale": "To answer this comparative growth question accurately, we need specific data points on Apple's stock performance and iPhone sales metrics. These queries target the precise financial information needed: company revenue trends, product-specific unit sales figures, and stock price movement over the same fiscal period for direct comparison.",
    "query": ["Apple total revenue growth fiscal year 2024", "iPhone unit sales growth fiscal year 2024", "Apple stock price growth fiscal year 2024"],
}}
```

Context: {search_topic}

""".strip()

web_search_instructions = """

Conduct targeted Google Searches to gather the most recent, credible information on "{research_topic}" and synthesize it into a verifiable text artifact.

Instructions:
- Query should ensure that the most current information is gathered. The current date is {current_date}.
- Conduct multiple, diverse searches to gather comprehensive information.
- Consolidate key findings while meticulously tracking the source(s) for each specific piece of information.
- The output should be a well-written summary or report based on your search findings. 
- Only include the information found in the search results, don't make up any information.

Research Topic:
{research_topic}

""".strip()

reflection_instructions = """
You are a research reviewer. Evaluate whether the provided summaries
contain enough information to answer the user's research topic.

Current date: {current_date}

Research topic:
{search_topic}

Research summaries:
{summaries}

Instructions:
- Identify important missing information, contradictions, or claims
  that need further verification.
- Set is_sufficient to true only when the topic is adequately covered.
- If more research is needed, describe the knowledge_gap and generate
  specific, self-contained follow_up_queries.
- Each query must include enough context to be searched independently.
- If the information is sufficient, set knowledge_gap to an empty
  string and follow_up_queries to an empty list.

Return the fields required by the provided output schema:
is_sufficient, knowledge_gap, follow_up_queries.
""".strip()

answer_instructions = """Generate a high-quality answer to the user's question based on the provided summaries.

Instructions:
- The current date is {current_date}.
- You are the final step of a multi-step research process, don't mention that you are the final step. 
- You have access to all the information gathered from the previous steps.
- You have access to the user's question.
- Generate a high-quality answer to the user's question based on the provided summaries and the user's question.
- Include the sources you used from the Summaries in the answer correctly, use markdown format (e.g. [apnews](https://vertexaisearch.cloud.google.com/id/1-0)). THIS IS A MUST.
- Never invent sources or citations.
- If the summaries lack verifiable sources, explicitly state that the answer could not be verified through web sources.
User Context:
- {research_topic}

Summaries:
{summaries}""".strip()
