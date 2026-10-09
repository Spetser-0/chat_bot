# Spetser AI - AI Skills System Documentation

**Last Updated**: 2026-10-05  
**Status**: ✅ Phase 4 IMPLEMENTED (service, prompts, variables, tools, routing, admin + public endpoints)

**Implementation map** (Phase 4):
- Service: `backend/app/services/skill_resolver.py` — SkillService (lookup, access gates, prompt build, classify)
- Prompt variables: `backend/app/utils/prompt_variables.py` — `{{user_name}}`, `{{language}}`, `{{current_date}}`, `{{subscription_tier}}`, `{{course_level}}` (unknown vars fail closed)
- Tool registry: `backend/app/services/tool_registry.py` — whitelist `web_search`, `calculator`; reserved-disabled `code_executor`, `file_reader`; validation only, no execution
- Admin API: `backend/app/api/v1/routes/admin/skills.py` — CRUD + `/{id}/test` + `/_meta/count`
- Public API: `backend/app/api/v1/routes/skills.py` — `GET /api/v1/skills`, `GET /api/v1/skills/{slug}` (no `system_prompt` exposed)
- Chat integration: `skill_slug` (explicit) or `"auto"` (classification with `general_assistant` fallback) on `POST /api/v1/chat/completions`

---

## Overview

The **Skills System** is the core feature that makes Spetser AI unique. Each skill represents a specialized AI personality with custom behavior, knowledge focus, and interaction style.

---

## Concept Explanation

### Child Explanation

A skill is like a costume for the AI robot. When the robot wears the "Math Teacher" costume, it becomes an expert at solving equations and explaining math step-by-step. When it wears the "Essay Helper" costume, it becomes good at organizing ideas and checking grammar.

Just like a real teacher might use different tools (a calculator for math class, a dictionary for writing class), our AI skills can use different tools depending on the costume they're wearing.

### Technical Explanation

A **Skill** is a database record that configures an LLM's behavior through:
- **System Prompt**: Instructions that define the AI's role and behavior
- **Temperature**: Controls creativity/randomness (0.0 = deterministic, 2.0 = very creative)
- **Model Preferences**: Which AI provider/model to use (with failover)
- **Tool Access**: Which functions the AI can call (web search, calculator, etc.)
- **Cost Settings**: Multiplier for credit pricing
- **Access Control**: Public/private, free/premium flags

---

## Skill Database Schema

```sql
CREATE TABLE skills (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    system_prompt TEXT NOT NULL,
    temperature NUMERIC(3,2) DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 4096,
    preferred_provider_id UUID REFERENCES ai_providers(id),
    fallback_provider_id UUID REFERENCES ai_providers(id),
    is_public BOOLEAN DEFAULT false,
    is_premium BOOLEAN DEFAULT false,
    cost_multiplier NUMERIC(4,2) DEFAULT 1.0,
    version INTEGER DEFAULT 1,
    created_by_user_id UUID REFERENCES students(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT temperature_range CHECK (temperature BETWEEN 0.0 AND 2.0),
    CONSTRAINT max_tokens_positive CHECK (max_tokens > 0),
    CONSTRAINT cost_multiplier_positive CHECK (cost_multiplier > 0)
);

CREATE TABLE skill_tools (
    id UUID PRIMARY KEY,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    tool_name VARCHAR(50) NOT NULL,
    tool_config JSONB,
    is_enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(skill_id, tool_name)
);

CREATE INDEX idx_skills_public ON skills(is_public) WHERE is_public = true;
CREATE INDEX idx_skills_premium ON skills(is_premium) WHERE is_premium = true;
CREATE INDEX idx_skill_tools_skill_id ON skill_tools(skill_id);
```

---

## Example Skills

### 1. Math Tutor

```python
{
    "slug": "math-tutor",
    "name": "Math Tutor",
    "description": "Patient math teacher for algebra, calculus, and problem-solving",
    "system_prompt": """You are an expert mathematics tutor.

Your role:
- Explain concepts step-by-step
- Break down complex problems into smaller parts
- Use examples and analogies
- Encourage students when they struggle
- Point out common mistakes
- Verify answers

User context:
- Student name: {{user_name}}
- Subscription: {{subscription_tier}}
- Date: {{current_date}}

Always respond in {{language}}. Use LaTeX for mathematical notation when needed.""",
    "temperature": 0.3,  # More deterministic for accuracy
    "max_tokens": 4096,
    "preferred_provider": "claude-3-5-sonnet",
    "fallback_provider": "gemini-1.5-pro",
    "is_public": true,
    "is_premium": false,
    "cost_multiplier": 1.0,
    "tools": ["calculator", "wolfram_alpha"]
}
```

### 2. Essay Helper

```python
{
    "slug": "essay-helper",
    "name": "Essay Writing Assistant",
    "description": "Helps structure arguments, improve writing, and provide feedback",
    "system_prompt": """You are an experienced writing coach specializing in academic essays.

Your role:
- Help students organize their ideas
- Suggest improvements to structure and flow
- Check grammar and style
- Provide constructive feedback
- Cite examples from literature when relevant
- Encourage original thinking

Guidelines:
- Do NOT write essays for students
- Help them develop their own ideas
- Ask questions to deepen their thinking
- Teach writing principles, not just fix errors

User: {{user_name}} ({{subscription_tier}})
Language: {{language}}""",
    "temperature": 0.7,  # Balanced creativity
    "max_tokens": 6000,
    "preferred_provider": "claude-3-5-sonnet",
    "fallback_provider": "gpt-4",
    "is_public": true,
    "is_premium": false,
    "cost_multiplier": 1.2,  # Longer responses = higher cost
    "tools": ["web_search"]
}
```

### 3. Code Reviewer (Premium)

```python
{
    "slug": "code-reviewer",
    "name": "Code Reviewer",
    "description": "Reviews code for bugs, style, and best practices",
    "system_prompt": """You are a senior software engineer conducting code reviews.

Your responsibilities:
- Identify bugs and logic errors
- Suggest improvements for readability and maintainability
- Point out security vulnerabilities
- Recommend best practices and design patterns
- Explain the reasoning behind your suggestions

Review style:
- Be constructive and respectful
- Explain WHY, not just WHAT to change
- Prioritize: Critical > Important > Nice-to-have
- Acknowledge good code practices too

Student: {{user_name}}
Focus: {{programming_language}} code""",
    "temperature": 0.5,
    "max_tokens": 8000,
    "preferred_provider": "claude-3-5-sonnet",
    "fallback_provider": "gpt-4",
    "is_public": true,
    "is_premium": true,  # Requires premium subscription
    "cost_multiplier": 1.5,
    "tools": ["code_linter", "documentation_search"]
}
```

### 4. Arabic Literature Expert

```python
{
    "slug": "arabic-literature",
    "name": "مرشد الأدب العربي",  # Arabic Literature Guide
    "description": "Expert in classical and modern Arabic literature",
    "system_prompt": """أنت خبير في الأدب العربي الكلاسيكي والحديث.

دورك:
- تحليل النصوص الأدبية العربية
- شرح البلاغة والأساليب
- مناقشة السياق التاريخي والثقافي
- الإجابة على أسئلة الطلاب حول الشعر والنثر
- مساعدة في فهم المعاني العميقة

المجالات:
- الشعر الجاهلي والعباسي
- الأدب الأندلسي
- الأدب الحديث والمعاصر
- البلاغة والنقد الأدبي

الطالب: {{user_name}}
التاريخ: {{current_date}}

تحدث دائماً بالعربية الفصحى.""",
    "temperature": 0.6,
    "max_tokens": 5000,
    "preferred_provider": "gemini-1.5-pro",  # Good multilingual support
    "fallback_provider": "gpt-4",
    "is_public": true,
    "is_premium": false,
    "cost_multiplier": 1.0,
    "tools": []
}
```

---

## Dynamic Prompt Variables

### Supported Variables

Skills can use template variables in `system_prompt`:

| Variable | Example Value | Source |
|----------|---------------|--------|
| `{{user_name}}` | "Ahmed Hassan" | `students.email` or profile |
| `{{language}}` | "Arabic" or "English" | User preference or auto-detect |
| `{{current_date}}` | "2026-10-04" | Server timestamp |
| `{{subscription_tier}}` | "free", "premium", "pro" | `students.is_premium` |
| `{{course_level}}` | "high_school", "university" | User profile (future) |
| `{{programming_language}}` | "Python" | Context from conversation (future) |

### Variable Injection (Phase 4)

```python
# app/services/skill_resolver.py

def inject_variables(prompt_template: str, user: Student, context: dict) -> str:
    """Replace template variables with actual values."""
    variables = {
        "user_name": user.email.split("@")[0].title(),  # Or use real name if we add it
        "language": context.get("language", "Arabic"),
        "current_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "subscription_tier": "premium" if user.is_premium else "free",
        "course_level": context.get("course_level", "university"),
        "programming_language": context.get("programming_language", "Python"),
    }
    
    result = prompt_template
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    
    return result
```

**Security Note**: Never inject user-controlled strings without validation. Only inject from trusted sources (database fields, server context).

---

## Skill Selection

### Method 1: Manual Selection (Phase 4)

User explicitly chooses skill from UI dropdown or sidebar:

```typescript
// Frontend: components/chat/SkillSelector.tsx
const skills = await api.get("/api/v1/skills");  // Public skills

<select onChange={(e) => setActiveSkill(e.target.value)}>
  <option value="">General Assistant</option>
  {skills.map(skill => (
    <option value={skill.slug} key={skill.slug}>
      {skill.name} {skill.is_premium && "👑"}
    </option>
  ))}
</select>
```

API request includes `skill_slug`:
```json
{
  "conversation_id": "...",
  "message": "Solve 2x + 5 = 13",
  "skill_slug": "math-tutor"
}
```

### Method 2: Automatic Routing (Phase 4 - Optional)

System auto-detects appropriate skill based on query:

```python
# app/services/intent_router.py (already exists, can extend)

async def classify_intent(message: str) -> str:
    """Use fast/cheap LLM to classify user intent."""
    classification_prompt = f"""Classify this user query into ONE category:

Categories:
- math: Mathematics, algebra, calculus, geometry
- essay: Writing, grammar, essays, literature analysis
- code: Programming, debugging, code review
- science: Physics, chemistry, biology
- language: Language learning, translation
- general: Everything else

User query: "{message}"

Category:"""
    
    response = await call_fast_llm(classification_prompt)  # Use cheap model like gpt-3.5-turbo
    intent = response.strip().lower()
    
    # Map intent to skill slug
    skill_map = {
        "math": "math-tutor",
        "essay": "essay-helper",
        "code": "code-reviewer",
        "science": "science-tutor",
        "language": "language-tutor",
    }
    
    return skill_map.get(intent, "general-assistant")
```

---

## Tool Registry (Phase 4)

### Available Tools

```python
# app/services/tool_registry.py

TOOL_DEFINITIONS = {
    "calculator": {
        "name": "calculator",
        "description": "Evaluate mathematical expressions",
        "parameters": {
            "expression": "string"
        },
        "function": evaluate_expression
    },
    
    "web_search": {
        "name": "web_search",
        "description": "Search the web for current information",
        "parameters": {
            "query": "string",
            "num_results": "integer (default: 5)"
        },
        "function": search_web
    },
    
    "wolfram_alpha": {
        "name": "wolfram_alpha",
        "description": "Query Wolfram Alpha for mathematical/scientific computations",
        "parameters": {
            "query": "string"
        },
        "function": query_wolfram
    },
    
    "code_linter": {
        "name": "code_linter",
        "description": "Run static analysis on code",
        "parameters": {
            "code": "string",
            "language": "string"
        },
        "function": lint_code
    },
}
```

### Tool Execution Flow

```
1. User message: "What's the square root of 144?"
2. LLM (with tools) decides to call calculator
3. LLM response: { "tool_call": { "name": "calculator", "args": { "expression": "sqrt(144)" } } }
4. Backend executes tool safely
5. Tool result: "12"
6. LLM continues: "The square root of 144 is 12."
7. Frontend displays full response
```

**Security**: 
- Whitelist allowed tools per skill
- Validate tool parameters
- Timeout tool execution (e.g., 10 seconds max)
- Sandbox dangerous operations (code execution)

---

## Skill Versioning (Future Enhancement)

Allow skills to evolve without breaking existing conversations:

```sql
ALTER TABLE skills ADD COLUMN version INTEGER DEFAULT 1;
ALTER TABLE messages ADD COLUMN skill_version INTEGER;
```

When skill is updated:
- Increment `skills.version`
- New conversations use latest version
- Old conversations replay with original version

---

## Cost Management

### Credit Calculation

```python
# app/services/credit_service.py

def calculate_message_cost(
    input_tokens: int,
    output_tokens: int,
    provider: AIProvider,
    skill: Skill
) -> Decimal:
    """Calculate credit cost for a message."""
    base_cost = (
        (input_tokens * provider.cost_input_per_1k / 1000) +
        (output_tokens * provider.cost_output_per_1k / 1000)
    )
    
    # Apply skill multiplier
    final_cost = base_cost * skill.cost_multiplier
    
    # Round to 4 decimal places
    return Decimal(final_cost).quantize(Decimal("0.0001"))
```

### Premium Skills

- `is_premium = true` skills require active subscription
- Check `user.is_premium` and `user.premium_expires_at`
- Return 403 if user tries to access premium skill without subscription

```python
async def check_skill_access(skill: Skill, user: Student):
    if skill.is_premium:
        if not user.is_premium:
            raise HTTPException(
                status_code=402,  # Payment Required
                detail="This skill requires a premium subscription"
            )
        if user.premium_expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=402,
                detail="Your premium subscription has expired"
            )
```

---

## Admin Skill Management (Phase 8)

### Endpoints

```python
# GET /api/v1/admin/skills
# List all skills (including private)

# POST /api/v1/admin/skills
# Create new skill

# GET /api/v1/admin/skills/{skill_id}
# Get skill details

# PATCH /api/v1/admin/skills/{skill_id}
# Update skill (increments version if prompt changed)

# DELETE /api/v1/admin/skills/{skill_id}
# Soft delete or mark inactive

# POST /api/v1/admin/skills/{skill_id}/test
# Test skill with sample query (admin preview)
```

### Skill Form (Frontend)

Fields:
- Name (text)
- Slug (text, unique, auto-generated from name)
- Description (textarea)
- System Prompt (large textarea with variable helper)
- Temperature (slider 0.0 - 2.0)
- Max Tokens (number input)
- Preferred Provider (dropdown)
- Fallback Provider (dropdown)
- Is Public (checkbox)
- Is Premium (checkbox)
- Cost Multiplier (number input, default 1.0)
- Allowed Tools (multi-select checkboxes)

**Variable Helper**: Insert button that shows available variables and inserts `{{variable_name}}` at cursor.

---

## Best Practices

### Writing Good System Prompts

1. **Define Role Clearly**: "You are a [role] who [responsibilities]"
2. **Set Boundaries**: What the AI should/shouldn't do
3. **Provide Context**: Use variables for personalization
4. **Give Examples**: Show desired response format
5. **Language Instruction**: Specify response language
6. **Tone Guidance**: Formal, casual, patient, strict, etc.

### Temperature Guidelines

- **0.0 - 0.3**: Factual, deterministic (math, code, translations)
- **0.4 - 0.7**: Balanced (general Q&A, tutoring)
- **0.8 - 1.2**: Creative (brainstorming, story writing)
- **1.3 - 2.0**: Very creative (poetry, experimental)

### Cost Multipliers

- `0.5`: Simple queries, cached responses
- `1.0`: Standard (default)
- `1.5`: Longer/deeper responses
- `2.0`: Research-heavy, tool usage

---

## Testing Skills

```python
# tests/unit/test_skill_prompt_injection.py

async def test_skill_prompt_injection():
    """Test that prompt variables are injected correctly."""
    user = Student(email="ahmed@example.com", is_premium=True)
    skill = Skill(
        system_prompt="Hello {{user_name}}, you have {{subscription_tier}} access."
    )
    
    result = inject_variables(skill.system_prompt, user, {})
    
    assert "Hello Ahmed, you have premium access." in result

async def test_premium_skill_requires_subscription():
    """Test that free users cannot access premium skills."""
    free_user = Student(is_premium=False)
    premium_skill = Skill(is_premium=True)
    
    with pytest.raises(HTTPException) as exc:
        await check_skill_access(premium_skill, free_user)
    
    assert exc.value.status_code == 402
```

---

## Future Enhancements

- **User-Created Skills**: Allow power users to create custom skills
- **Skill Marketplace**: Users share/sell skills
- **Skill Analytics**: Track which skills are most popular
- **A/B Testing**: Test multiple prompt variations
- **Context Windows**: Optimize prompt length for model limits
- **Multi-Turn Tools**: Tools that require multiple interactions
- **Skill Chaining**: One skill calls another for complex tasks

---

**End of AI Skills Documentation**
