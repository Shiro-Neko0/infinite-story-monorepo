from story.utils import cut_trailing_sentence
import warnings
from gpt2.src import encoder
import json
from tensorflow.contrib.util import make_tensor_proto
import os

import grpc
import numpy

from tensorflow_serving.apis import predict_pb2
from tensorflow_serving.apis import prediction_service_pb2_grpc

warnings.filterwarnings("ignore")


class GPT2GeneratorSavedModel:
    def __init__(self, generate_num=60, temperature=0.4, top_k=40, top_p=0.9):
        self.generate_num = generate_num
        self.temp = temperature
        self.top_k = top_k
        self.top_p = top_p

        model_dir = "gpt2/encoders"
        # self.checkpoint_path = os.path.join(self.model_dir, self.model_name)
        self.hostport = "0.0.0.0:8500"
        self.channel = grpc.insecure_channel(self.hostport)
        self.stub = prediction_service_pb2_grpc.PredictionServiceStub(
            self.channel)
        self.enc = encoder.get_encoder(model_dir)
        # hparams = model.default_hparams()
        # with open(os.path.join(models_dir, self.model_name, "hparams.json")) as f:
        #     hparams.override_from_dict(json.load(f))
        # seed = np.random.randint(0, 100000)

        # config = tf.compat.v1.ConfigProto()
        # config.gpu_options.allow_growth = True
        # self.sess = tf.compat.v1.Session(config=config)

        # self.context = tf.placeholder(tf.int32, [self.batch_size, None])
        # # np.random.seed(seed)
        # # tf.set_random_seed(seed)
        # self.output = sample.sample_sequence(
        #     hparams=hparams,
        #     length=self.generate_num,
        #     context=self.context,
        #     batch_size=self.batch_size,
        #     temperature=temperature,
        #     top_k=top_k,
        #     top_p=top_p,
        # )

        # saver = tf.train.Saver()
        # ckpt = tf.train.latest_checkpoint(
        #     os.path.join(models_dir, self.model_name))
        # saver.restore(self.sess, ckpt)

    def prompt_replace(self, prompt):
        # print("\n\nBEFORE PROMPT_REPLACE:")
        # print(repr(prompt))
        if len(prompt) > 0 and prompt[-1] == " ":
            prompt = prompt[:-1]

        # prompt = second_to_first_person(prompt)

        # print("\n\nAFTER PROMPT_REPLACE")
        # print(repr(prompt))
        return prompt

    def result_replace(self, result):
        print("\n\nBEFORE RESULT_REPLACE:")
        print(repr(result))

        result = cut_trailing_sentence(result)
        if len(result) < 2:
            return ""
        first_letter_capitalized = result[0].isupper()
        result = result.replace('."', '".')
        result = result.replace("#", "")
        result = result.replace("*", "")
        result = result.replace("\n\n", "\n")
        # result = first_to_second_person(result)

        if not first_letter_capitalized:
            result = result[0].lower() + result[1:]

        if result[-1] == " ":
            result = result[:-1]
            if result[-1] not in [".", "!", "?"]:
                result = result + "."
        elif result[-1] != "." and result[-1] != "\n":
            result = result + "."
        elif result[-1] == "\n" and result[-2] not in [".", "!", "?"]:
            result = result[:-2] + ".\n"
        print("\n\nAFTER RESULT_REPLACE:")
        print(repr(result))
        return result

    def generate_raw(self, prompt):
        context_tokens = self.enc.encode(prompt)
        request = predict_pb2.PredictRequest()
        request.model_spec.name = 'generator'
        request.inputs['context'].CopyFrom(make_tensor_proto([
            context_tokens]))
        result = self.stub.Predict(request, 20.0)  # 10 seconds
        out = result.outputs['output'].int_val[len(context_tokens):]

        text = self.enc.decode(out)
        return text

    def generate(self, prompt, options=None, seed=1, no_loop=False):

        debug_print = True
        prompt = self.prompt_replace(prompt)

        if debug_print:
            print("******DEBUG******")
            print("Prompt is: ", repr(prompt))

        text = self.generate_raw(prompt)

        if debug_print:
            print("Generated result is: ", repr(text))
            print("******END DEBUG******")

        result = text
        result = self.result_replace(result)
        # No loop here, loop in the thing sending the request. You want FIFO man
        if len(result) == 0:
            return False

        return result