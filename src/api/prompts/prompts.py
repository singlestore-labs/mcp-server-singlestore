from src.api.prompts.types import Prompt

prompts_definitions = []

# Export the prompts using create_from_dict for consistency
prompts = [Prompt.create_from_dict(prompt) for prompt in prompts_definitions]
