from typing import Optional
import torch
import torchvision.transforms as T
from torchvision.transforms import InterpolationMode
from transformers import AutoModel, AutoTokenizer, GenerationConfig
from huggingface_hub import snapshot_download


from hydra_vl4ai.util.misc import get_root_folder
from hydra_vl4ai.tool._base import BaseModel, module_registry


IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


@module_registry.register("internvl2")
class InternVL2(BaseModel):
    model_name = "OpenGVLab/InternVL2-8B"

    def __init__(self, gpu_number=0):
        super().__init__(gpu_number)
        self.model_name_id = self.model_name.split("/")[-1]
        path = get_root_folder() / "pretrained_models" / "internvl2" / self.model_name_id

        if not path.exists():
            self.prepare()

        self.model = AutoModel.from_pretrained(
            path,
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True,
            trust_remote_code=True).eval().to(self.dev)
        self.tokenizer = AutoTokenizer.from_pretrained(path, trust_remote_code=True, use_fast=False)
        self.generation_config = dict(max_new_tokens=1024, do_sample=False)

    def forward(self, input_image, query, *_, **__):
        pixel_values = load_image(input_image).to(torch.bfloat16).cuda(self.dev)
        return self.chat(self.tokenizer, pixel_values, query, self.generation_config)
    
    @torch.no_grad()
    def forward_next_word_prediction(self, input_image, query, alternatives: list[str]):
        pixel_values = load_image(input_image).to(torch.bfloat16).cuda(self.dev)
        return self.get_next_word_prediction(self.tokenizer, pixel_values, query, self.generation_config, alternatives)

    @torch.no_grad()
    def prepare_multimodal_inputs(self, tokenizer, pixel_values, question, generation_config, history=None,
             num_patches_list=None, IMG_START_TOKEN='<img>', IMG_END_TOKEN='</img>', IMG_CONTEXT_TOKEN='<IMG_CONTEXT>',
             verbose=False):
        # overwrite the default `chat` method in the InternVL2 model to fix the problem if you're not using cuda:0
        import importlib
        module = importlib.import_module(f'transformers_modules.{self.model_name_id}.conversation')
        get_conv_template = getattr(module, 'get_conv_template')

        if history is None and pixel_values is not None and '<image>' not in question:
            question = '<image>\n' + question

        if num_patches_list is None:
            num_patches_list = [pixel_values.shape[0]] if pixel_values is not None else []
        assert pixel_values is None or len(pixel_values) == sum(num_patches_list)

        img_context_token_id = tokenizer.convert_tokens_to_ids(IMG_CONTEXT_TOKEN)
        self.model.img_context_token_id = img_context_token_id

        template = get_conv_template(self.model.template)
        template.system_message = self.model.system_message
        eos_token_id = tokenizer.convert_tokens_to_ids(template.sep)

        history = [] if history is None else history
        for (old_question, old_answer) in history:
            template.append_message(template.roles[0], old_question)
            template.append_message(template.roles[1], old_answer)
        template.append_message(template.roles[0], question)
        template.append_message(template.roles[1], None)
        query = template.get_prompt()

        if verbose and pixel_values is not None:
            image_bs = pixel_values.shape[0]
            print(f'dynamic ViT batch size: {image_bs}')

        for num_patches in num_patches_list:
            image_tokens = IMG_START_TOKEN + IMG_CONTEXT_TOKEN * self.model.num_image_token * num_patches + IMG_END_TOKEN
            query = query.replace('<image>', image_tokens, 1)

        model_inputs = tokenizer(query, return_tensors='pt')
        input_ids = model_inputs['input_ids'].to(self.dev)
        attention_mask = model_inputs['attention_mask'].to(self.dev)
        generation_config['eos_token_id'] = eos_token_id
        return input_ids, attention_mask, generation_config, history, template, query
    
    @torch.no_grad()
    def prepare_lm_generator_inputs(
            self,
            pixel_values: Optional[torch.FloatTensor] = None,
            input_ids: Optional[torch.FloatTensor] = None,
            attention_mask: Optional[torch.LongTensor] = None,
            visual_features: Optional[torch.FloatTensor] = None,
            generation_config: Optional[GenerationConfig] = None,
            output_hidden_states: Optional[bool] = None,
            return_dict: Optional[bool] = None,
            **generate_kwargs,
    ) -> dict:

        assert self.model.img_context_token_id is not None
        if pixel_values is not None:
            if visual_features is not None:
                vit_embeds = visual_features
            else:
                vit_embeds = self.model.extract_feature(pixel_values)
            input_embeds = self.model.language_model.get_input_embeddings()(input_ids)
            B, N, C = input_embeds.shape
            input_embeds = input_embeds.reshape(B * N, C)

            input_ids = input_ids.reshape(B * N)
            selected = (input_ids == self.model.img_context_token_id)
            assert selected.sum() != 0
            input_embeds[selected] = vit_embeds.reshape(-1, C).to(input_embeds.device)

            input_embeds = input_embeds.reshape(B, N, C)
        else:
            input_embeds = self.model.language_model.get_input_embeddings()(input_ids)

        return dict(
            inputs_embeds=input_embeds,
            attention_mask=attention_mask,
            generation_config=generation_config,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
            use_cache=True,
            **generate_kwargs,
        )

    @torch.no_grad()
    def chat(self, tokenizer, pixel_values, question, generation_config, history=None, return_history=False,
             IMG_START_TOKEN='<img>', IMG_END_TOKEN='</img>', IMG_CONTEXT_TOKEN='<IMG_CONTEXT>',
             verbose=False):
        
        input_ids, attention_mask, generation_config, history, template, query = self.prepare_multimodal_inputs(
            tokenizer, pixel_values, question, generation_config, history, verbose=verbose)

        generation_output = self.model.generate(
            pixel_values=pixel_values,
            input_ids=input_ids,
            attention_mask=attention_mask,
            **generation_config
        )
        response = tokenizer.batch_decode(generation_output, skip_special_tokens=True)[0]
        response = response.split(template.sep)[0].strip()
        history.append((question, response))
        if return_history:
            return response, history
        else:
            query_to_print = query.replace(IMG_CONTEXT_TOKEN, '')
            query_to_print = query_to_print.replace(f'{IMG_START_TOKEN}{IMG_END_TOKEN}', '<image>')
            if verbose:
                print(query_to_print, response)
            return response

    @torch.no_grad()
    def get_next_word_prediction(self, tokenizer, pixel_values, question, generation_config, alternatives: list[str], history=None,
        verbose=False
    ):
    
        input_ids, attention_mask, generation_config, history, template, query = self.prepare_multimodal_inputs(
            tokenizer, pixel_values, question, generation_config, history, verbose=verbose)
        
        lm_generator_inputs = self.prepare_lm_generator_inputs(
            pixel_values=pixel_values,
            input_ids=input_ids,
            attention_mask=attention_mask,
            **generation_config
        )

        del lm_generator_inputs["generation_config"]
        del lm_generator_inputs["max_new_tokens"]
        del lm_generator_inputs["do_sample"]
        del lm_generator_inputs["eos_token_id"]

        predictions = self.model.language_model(**lm_generator_inputs)[0] # logits
        
        # Get the next token candidates.
        next_token_candidates_tensor = predictions[0, -1, :]


        # Convert alternative words to token IDs.
        alternative_token_ids = [self.tokenizer.encode(word, add_special_tokens=False)[0] for word in alternatives]

        # Filter logits to only keep the alternative token IDs.
        alternative_logits = next_token_candidates_tensor[alternative_token_ids]

        # Calculate probabilities for the alternative words.
        alternative_probabilities = torch.nn.functional.softmax(alternative_logits, dim=-1).tolist()

        # normalie the probabilities to 1 to minimize the floating point error
        sum_prob = sum(alternative_probabilities)
        alternative_probabilities = [p / sum_prob for p in alternative_probabilities]

        # Return the alternatives and their probabilities.
        return list(zip(alternatives, alternative_probabilities))


    @classmethod
    def prepare(cls):
        snapshot_download(cls.model_name,
            local_dir=get_root_folder() / "pretrained_models" / "internvl2" / cls.model_name.split("/")[-1])


# ===============================
# InternVL2 helper functions, from https://internvl.readthedocs.io/en/latest/internvl2.0/quick_start.html
def build_transform(input_size):
    MEAN, STD = IMAGENET_MEAN, IMAGENET_STD
    transform = T.Compose([
        T.Lambda(lambda img: img.convert('RGB') if img.mode != 'RGB' else img),
        T.Resize((input_size, input_size), interpolation=InterpolationMode.BICUBIC),
        T.ToTensor(),
        T.Normalize(mean=MEAN, std=STD)
    ])
    return transform


def find_closest_aspect_ratio(aspect_ratio, target_ratios, width, height, image_size):
    best_ratio_diff = float('inf')
    best_ratio = (1, 1)
    area = width * height
    for ratio in target_ratios:
        target_aspect_ratio = ratio[0] / ratio[1]
        ratio_diff = abs(aspect_ratio - target_aspect_ratio)
        if ratio_diff < best_ratio_diff:
            best_ratio_diff = ratio_diff
            best_ratio = ratio
        elif ratio_diff == best_ratio_diff:
            if area > 0.5 * image_size * image_size * ratio[0] * ratio[1]:
                best_ratio = ratio
    return best_ratio


def dynamic_preprocess(image, min_num=1, max_num=12, image_size=448, use_thumbnail=False):
    orig_width, orig_height = image.size
    aspect_ratio = orig_width / orig_height

    # calculate the existing image aspect ratio
    target_ratios = set(
        (i, j) for n in range(min_num, max_num + 1) for i in range(1, n + 1) for j in range(1, n + 1) if
        i * j <= max_num and i * j >= min_num)
    target_ratios = sorted(target_ratios, key=lambda x: x[0] * x[1])

    # find the closest aspect ratio to the target
    target_aspect_ratio = find_closest_aspect_ratio(
        aspect_ratio, target_ratios, orig_width, orig_height, image_size)

    # calculate the target width and height
    target_width = image_size * target_aspect_ratio[0]
    target_height = image_size * target_aspect_ratio[1]
    blocks = target_aspect_ratio[0] * target_aspect_ratio[1]

    # resize the image
    resized_img = image.resize((target_width, target_height))
    processed_images = []
    for i in range(blocks):
        box = (
            (i % (target_width // image_size)) * image_size,
            (i // (target_width // image_size)) * image_size,
            ((i % (target_width // image_size)) + 1) * image_size,
            ((i // (target_width // image_size)) + 1) * image_size
        )
        # split the image
        split_img = resized_img.crop(box)
        processed_images.append(split_img)
    assert len(processed_images) == blocks
    if use_thumbnail and len(processed_images) != 1:
        thumbnail_img = image.resize((image_size, image_size))
        processed_images.append(thumbnail_img)
    return processed_images


def load_image(image_tensor, input_size=448, max_num=12):
    image = T.functional.to_pil_image(image_tensor)
    transform = build_transform(input_size=input_size)
    images = dynamic_preprocess(image, image_size=input_size, use_thumbnail=True, max_num=max_num)
    pixel_values = [transform(image) for image in images]
    pixel_values = torch.stack(pixel_values)
    return pixel_values
