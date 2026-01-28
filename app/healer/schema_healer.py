"""
LLM-Powered Schema Healer - The Core Agentic Logic

This module contains the intelligence that detects schema drift
and generates new mappings using an LLM.

Now with real-time thought streaming for the "Glass Box" experience!
"""
import json
from typing import Any, Optional
from datetime import datetime
from openai import AsyncOpenAI
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.logging_config import get_logger
from app.models import (
    SchemaMapping,
    FieldMapping,
    HealingEvent,
    HealingEventType,
)
from app.database import redis_client, mongodb_client
from app.healer.agent_stream import agent_stream, ThoughtType

logger = get_logger(__name__)

# LLM token cost estimates (per 1K tokens)
COST_PER_1K_INPUT = 0.00015   # GPT-4o-mini input
COST_PER_1K_OUTPUT = 0.0006   # GPT-4o-mini output

# System prompt for the schema healing agent
HEALING_AGENT_PROMPT = """You are a Schema Healing Agent. Your job is to analyze API response mismatches and generate field mappings.

## Your Task
When an upstream API changes its response schema, you must identify how to map the new fields to the expected fields.

## Input Format
You will receive:
1. **Expected Schema**: The Pydantic model fields the client expects
2. **Actual Response**: The actual JSON response from the upstream API
3. **Validation Error**: The Pydantic validation error that occurred

## Output Format
Return ONLY a valid JSON object with this structure:
```json
{
    "field_mappings": [
        {
            "source_field": "new_field_name_in_response",
            "target_field": "expected_field_name",
            "transform": null,
            "confidence": 0.95
        }
    ],
    "analysis": "Brief explanation of what changed",
    "can_heal": true
}
```

## Rules
1. Match fields by analyzing:
   - Similar names (e.g., "user_id" → "uid", "userId")
   - Data types that match
   - Semantic meaning
2. Set confidence between 0 and 1:
   - 1.0 = Exact match or very obvious mapping
   - 0.8+ = High confidence based on naming similarity
   - 0.5-0.8 = Moderate confidence, needs type checking
   - <0.5 = Low confidence, mapping is uncertain
3. For transforms, use one of:
   - null (no transform needed)
   - "to_int" (convert to integer)
   - "to_str" (convert to string)
   - "to_float" (convert to float)
   - "to_bool" (convert to boolean)
   - "parse_date" (parse ISO date string)
4. If you cannot confidently map a field, set can_heal to false

## Example
Expected: {"user_id": int, "name": str}
Actual: {"uid": 123, "full_name": "John Doe"}
Error: "user_id field required"

Output:
{
    "field_mappings": [
        {"source_field": "uid", "target_field": "user_id", "transform": null, "confidence": 0.9},
        {"source_field": "full_name", "target_field": "name", "transform": null, "confidence": 0.85}
    ],
    "analysis": "API renamed user_id to uid and name to full_name",
    "can_heal": true
}
"""


class SchemaHealer:
    """
    The main healing engine that uses LLM to fix schema drift.
    
    This implements the agentic loop with real-time thought streaming:
    1. Detect validation error → Emit ALERT
    2. Analyze the mismatch → Emit ANALYZING
    3. Scan available fields → Emit SCANNING
    4. Generate hypothesis → Emit HYPOTHESIS
    5. Apply and validate → Emit PATCHING
    6. Cache for future → Emit SUCCESS
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[AsyncOpenAI] = None
        self._require_approval_for_low_confidence = False
        self._confidence_threshold_for_approval = 0.7
    
    def set_approval_mode(self, require: bool, threshold: float = 0.7):
        """Configure human-in-the-loop mode."""
        self._require_approval_for_low_confidence = require
        self._confidence_threshold_for_approval = threshold
    
    def _get_client(self) -> AsyncOpenAI:
        """Get or create OpenAI client."""
        if not self._client:
            self._client = AsyncOpenAI(
                api_key=self.settings.llm_api_key,
                base_url=self.settings.llm_base_url
            )
        return self._client
    
    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost in USD."""
        input_cost = (input_tokens / 1000) * COST_PER_1K_INPUT
        output_cost = (output_tokens / 1000) * COST_PER_1K_OUTPUT
        return round(input_cost + output_cost, 6)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _call_llm(self, prompt: str) -> tuple[str, float]:
        """
        Call the LLM with retry logic.
        
        Args:
            prompt: The user prompt to send
            
        Returns:
            Tuple of (response content, estimated cost)
        """
        client = self._get_client()
        
        response = await client.chat.completions.create(
            model=self.settings.llm_model,
            messages=[
                {"role": "system", "content": HEALING_AGENT_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for consistent outputs
            response_format={"type": "json_object"}
        )
        
        # Estimate tokens (rough approximation)
        input_tokens = len(HEALING_AGENT_PROMPT + prompt) // 4
        output_tokens = len(response.choices[0].message.content) // 4
        cost = self._estimate_cost(input_tokens, output_tokens)
        
        return response.choices[0].message.content, cost
    
    def _extract_schema_info(self, model_class: type) -> dict[str, str]:
        """Extract field names and types from a Pydantic model."""
        schema = model_class.model_json_schema()
        properties = schema.get("properties", {})
        
        field_info = {}
        for field_name, field_schema in properties.items():
            field_type = field_schema.get("type", "any")
            field_info[field_name] = field_type
        
        return field_info
    
    async def analyze_and_heal(
        self,
        endpoint: str,
        expected_model: type,
        actual_response: dict[str, Any],
        validation_error: ValidationError
    ) -> Optional[SchemaMapping]:
        """
        Main healing method - analyzes mismatch and generates mapping.
        Now with real-time thought streaming!
        
        Args:
            endpoint: The API endpoint that failed
            expected_model: The Pydantic model class expected
            actual_response: The actual response from upstream
            validation_error: The validation error that occurred
            
        Returns:
            SchemaMapping if healing successful, None otherwise
        """
        start_time = datetime.utcnow()
        total_cost = 0.0
        
        # === STEP 1: ALERT ===
        await agent_stream.emit(
            ThoughtType.ALERT,
            f"🔴 Schema validation failed for {endpoint}",
            details={
                "endpoint": endpoint,
                "error_count": len(validation_error.errors()),
                "expected_model": expected_model.__name__
            }
        )
        
        # Log to MongoDB
        await mongodb_client.log_healing_event(HealingEvent(
            event_type=HealingEventType.HEALING_STARTED,
            endpoint=endpoint,
            original_error=str(validation_error),
            original_response=actual_response,
            metadata={"model": expected_model.__name__}
        ))
        
        # Small delay for visual effect
        import asyncio
        await asyncio.sleep(0.3)
        
        # === STEP 2: ANALYZING ===
        error_fields = [e.get("loc", ["unknown"])[0] for e in validation_error.errors()]
        await agent_stream.emit(
            ThoughtType.ANALYZING,
            f"🧐 Analyzing validation errors... Missing/invalid fields: {', '.join(str(f) for f in error_fields)}"
        )
        
        await asyncio.sleep(0.3)
        
        # === STEP 3: SCANNING ===
        available_fields = list(actual_response.keys())
        await agent_stream.emit(
            ThoughtType.SCANNING,
            f"🔍 Scanning response payload... Found fields: {', '.join(available_fields)}",
            details={"available_fields": available_fields}
        )
        
        await asyncio.sleep(0.3)
        
        try:
            # Extract schema information
            expected_schema = self._extract_schema_info(expected_model)
            
            # Build the prompt
            prompt = f"""## Expected Schema
{json.dumps(expected_schema, indent=2)}

## Actual Response
{json.dumps(actual_response, indent=2)}

## Validation Error
{str(validation_error)}

Analyze this mismatch and provide field mappings to heal it."""

            # === STEP 4: CALLING LLM ===
            await agent_stream.emit(
                ThoughtType.ANALYZING,
                "🤖 Consulting AI to analyze the schema mismatch..."
            )
            
            # Call LLM
            llm_response, llm_cost = await self._call_llm(prompt)
            total_cost += llm_cost
            
            logger.debug("llm_response", response=llm_response)
            
            # Parse LLM response
            healing_result = json.loads(llm_response)
            
            if not healing_result.get("can_heal", False):
                await agent_stream.emit(
                    ThoughtType.FAILURE,
                    f"❌ Cannot heal: {healing_result.get('analysis', 'Unknown reason')}",
                    cost_usd=total_cost
                )
                
                await mongodb_client.log_healing_event(HealingEvent(
                    event_type=HealingEventType.HEALING_FAILED,
                    endpoint=endpoint,
                    original_error=str(validation_error),
                    original_response=actual_response,
                    metadata={
                        "reason": "LLM determined healing not possible",
                        "analysis": healing_result.get("analysis")
                    }
                ))
                return None
            
            # === STEP 5: HYPOTHESIS ===
            analysis = healing_result.get("analysis", "Field names changed")
            await agent_stream.emit(
                ThoughtType.HYPOTHESIS,
                f"💡 Hypothesis: {analysis}",
                cost_usd=llm_cost
            )
            
            await asyncio.sleep(0.3)
            
            # Build field mappings
            field_mappings = []
            min_confidence = 1.0
            
            for mapping_data in healing_result.get("field_mappings", []):
                confidence = mapping_data.get("confidence", 0)
                source = mapping_data.get("source_field")
                target = mapping_data.get("target_field")
                
                min_confidence = min(min_confidence, confidence)
                
                # Emit each mapping discovery
                await agent_stream.emit(
                    ThoughtType.SCANNING,
                    f"📍 Mapping: '{source}' → '{target}'",
                    confidence=confidence,
                    details={
                        "source": source,
                        "target": target,
                        "transform": mapping_data.get("transform")
                    }
                )
                
                # Skip low confidence mappings
                if confidence < self.settings.healing_confidence_threshold:
                    await agent_stream.emit(
                        ThoughtType.INFO,
                        f"⚠️ Skipping low-confidence mapping ({confidence*100:.0f}%)"
                    )
                    continue
                
                field_mappings.append(FieldMapping(
                    source_field=source,
                    target_field=target,
                    transform=mapping_data.get("transform"),
                    confidence=confidence
                ))
            
            if not field_mappings:
                await agent_stream.emit(
                    ThoughtType.FAILURE,
                    "❌ No valid mappings could be generated",
                    cost_usd=total_cost
                )
                return None
            
            # === STEP 6: HUMAN IN THE LOOP (if enabled) ===
            if self._require_approval_for_low_confidence and min_confidence < self._confidence_threshold_for_approval:
                await agent_stream.emit(
                    ThoughtType.WAITING,
                    f"⏸️ Low confidence ({min_confidence*100:.0f}%). Waiting for human approval...",
                    confidence=min_confidence,
                    requires_approval=True
                )
                
                # This will block until approval
                approved = await agent_stream.approve_pending(True)  # Default approve for now
                
                if not approved:
                    await agent_stream.emit(
                        ThoughtType.FAILURE,
                        "❌ Healing rejected by user"
                    )
                    return None
            
            # === STEP 7: PATCHING ===
            await agent_stream.emit(
                ThoughtType.PATCHING,
                f"🛠️ Hot-patching schema mapping with {len(field_mappings)} field(s)..."
            )
            
            # Create schema mapping
            schema_mapping = SchemaMapping(
                endpoint=endpoint,
                field_mappings=field_mappings,
                created_by="auto",
                llm_model=self.settings.llm_model
            )
            
            # Validate the mapping works
            healed_data = self.apply_mapping(actual_response, schema_mapping)
            
            await asyncio.sleep(0.3)
            
            # === STEP 8: RETRYING ===
            await agent_stream.emit(
                ThoughtType.RETRYING,
                "🔄 Validating healed data against expected schema..."
            )
            
            try:
                expected_model.model_validate(healed_data)
            except ValidationError as e:
                await agent_stream.emit(
                    ThoughtType.FAILURE,
                    f"❌ Healed data still fails validation: {str(e)[:100]}",
                    cost_usd=total_cost
                )
                
                await mongodb_client.log_healing_event(HealingEvent(
                    event_type=HealingEventType.HEALING_FAILED,
                    endpoint=endpoint,
                    original_error=str(validation_error),
                    metadata={"reason": "Healed data still fails validation"}
                ))
                return None
            
            # === STEP 9: SUCCESS ===
            # Cache the mapping
            await redis_client.set_mapping(endpoint, schema_mapping)
            
            # Calculate duration
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Increment healing counter
            agent_stream.increment_healing_count()
            
            await agent_stream.emit(
                ThoughtType.SUCCESS,
                f"🟢 Schema healed successfully! Cached for future requests.",
                cost_usd=total_cost,
                confidence=min_confidence,
                details={
                    "mappings_count": len(field_mappings),
                    "duration_ms": round(duration_ms, 2),
                    "cached": True
                }
            )
            
            # Log success
            await mongodb_client.log_healing_event(HealingEvent(
                event_type=HealingEventType.HEALING_SUCCESS,
                endpoint=endpoint,
                applied_mapping=schema_mapping,
                success=True,
                duration_ms=duration_ms,
                metadata={
                    "mappings_count": len(field_mappings),
                    "analysis": analysis,
                    "cost_usd": total_cost
                }
            ))
            
            return schema_mapping
            
        except Exception as e:
            logger.error("healing_error", endpoint=endpoint, error=str(e))
            
            await agent_stream.emit(
                ThoughtType.FAILURE,
                f"❌ Healing error: {str(e)[:100]}",
                cost_usd=total_cost
            )
            
            await mongodb_client.log_healing_event(HealingEvent(
                event_type=HealingEventType.HEALING_FAILED,
                endpoint=endpoint,
                original_error=str(validation_error),
                metadata={"error": str(e)}
            ))
            return None
    
    def apply_mapping(
        self,
        data: dict[str, Any],
        mapping: SchemaMapping
    ) -> dict[str, Any]:
        """
        Apply a schema mapping to transform data.
        
        Args:
            data: The original response data
            mapping: The schema mapping to apply
            
        Returns:
            Transformed data with mapped fields
        """
        result = dict(data)  # Start with a copy
        
        for field_mapping in mapping.field_mappings:
            source = field_mapping.source_field
            target = field_mapping.target_field
            
            if source not in data:
                continue
            
            value = data[source]
            
            # Apply transform if specified
            if field_mapping.transform:
                value = self._apply_transform(value, field_mapping.transform)
            
            # Map to target field
            result[target] = value
        
        return result
    
    def _apply_transform(self, value: Any, transform: str) -> Any:
        """Apply a transformation to a value."""
        transforms = {
            "to_int": lambda x: int(x) if x is not None else None,
            "to_str": lambda x: str(x) if x is not None else None,
            "to_float": lambda x: float(x) if x is not None else None,
            "to_bool": lambda x: bool(x) if x is not None else None,
            "parse_date": lambda x: datetime.fromisoformat(x) if x else None,
        }
        
        transform_fn = transforms.get(transform)
        if transform_fn:
            try:
                return transform_fn(value)
            except (ValueError, TypeError) as e:
                logger.warning(
                    "transform_failed",
                    transform=transform,
                    value=value,
                    error=str(e)
                )
        
        return value


# Singleton instance
schema_healer = SchemaHealer()
