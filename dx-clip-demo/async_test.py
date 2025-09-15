import os
import numpy as np
import argparse
from dx_engine import InferenceEngine
import time
import threading
import queue  

callback_cnt = 0
callback_lock = threading.Lock()
result_queue = queue.Queue()  
start_time = 0
end_time = 0
def parse_args():
    parser = argparse.ArgumentParser(description="Inference Engine Arguments")
    parser.add_argument("--model", "-m", type=str, required=True, help="Path to model file (.dxnn)")
    parser.add_argument("--input", "-i", type=str, default="", help="Path to input data file")
    parser.add_argument("--output", "-o", type=str, default="output.bin.pyrt", help="Path to output data file")
    parser.add_argument("--benchmark", "-b", action="store_true", default=False, help="Run benchmark test")
    parser.add_argument("--loops", "-l", type=int, default=1, help="Number of inference loops")

    args = parser.parse_args()

    if not os.path.exists(args.model):
        parser.error(f"Model path '{args.model}' does not exist.")
    if args.input and not os.path.exists(args.input):
        parser.error(f"Input file '{args.input}' does not exist.")
    return args

def callback_with_args(outputs, user_arg):
    global callback_cnt
    with callback_lock:
        print(f"Callback triggered for inference with user_arg({user_arg.value.unique_id})")
        callback_cnt += 1
        x = outputs[0][:, 0]
        x = x / np.linalg.norm(x, axis=-1, keepdims=True)
        print(x.shape)
        result_queue.get(timeout=5) 
        result_queue.task_done() 
    return 0

def register_callback(outputs, arguments):
    with callback_lock:
        print(f"Callback triggered for inference with user_arg({arguments.value.unique_id})")
        x = outputs[0][:, 0]
        x = x / np.linalg.norm(x, axis=-1, keepdims=True)
        print(x.shape)
        result_queue.get(timeout=5) 
        result_queue.task_done() 
    return 0

class TestArguments:
    def __init__(self, ie: InferenceEngine, name, age, unique_id):
        self.ie = ie
        self.name = name
        self.age = age
        self.unique_id = unique_id
        
        self.ie.register_callback(self.pp_callback)
    
    def run_async(self, x):
        self.ie.run_async([x], self)
        return 0
    
    @staticmethod
    def pp_callback(outputs, arg):
        test = arg.value
        print(".................................>> ", test.unique_id)
        result_queue.get(timeout=5) 
        result_queue.task_done() 
        return 0

if __name__ == "__main__":
    args = parse_args()
        

    print("---------------------------------")
    print(f"Loading model from: {args.model}")
    print("---------------------------------")

    # Initialize inference engine
    ie = InferenceEngine(args.model)
    input_dtype = ie.input_dtype()
    output_dtype = ie.output_dtype()
    input_size = ie.input_size()
    output_size = ie.output_size()
    
    # test_args = []
    # for i in range(args.loops):
    #     test_args.append(TestArguments(ie, "test", 10 + i, "F"))

    print(f"Input data type: {input_dtype}")
    print(f"Output data type: {output_dtype}")
    print(f"Input size: {input_size}")
    print(f"Total output size: {output_size}")

    # Load input data if provided, otherwise use zeros
    if args.input:
        with open(args.input, "rb") as file:
            if input_dtype[0] is "INT8":
                input_data = [np.frombuffer(file.read(), dtype=np.int8)]
            elif input_dtype[0] is "UINT8":
                input_data = [np.frombuffer(file.read(), dtype=np.uint8)]
    else:
        input_data = [np.zeros((224, 224, 3), dtype=np.uint8)]

    # Register callback function
    # ie.register_callback(callback_with_args)
    
    test_args = []
    for i in range(5):
        test_args.append(TestArguments(ie, "test", 30, i))
    
    unique_id = 0

    start_time = time.time()
    # Run inference for the number of loops specified
    for loop in range(args.loops):
        test_arg:TestArguments = test_args[unique_id]
        x = input_data[0].astype(np.float32)
        x = x * np.float32([64.75055694580078]) + np.float32([-11.950003623962402])
        x = x.round().clip(-128, 127)
        x = x.astype(np.int8)
        x = np.reshape(x, [1, 3, 7, 32, 7, 32])
        x = np.transpose(x, [0, 2, 4, 3, 5, 1])
        x = np.reshape(x, [1, 49, 48, 64])
        x = np.transpose(x, [0, 2, 1, 3])
        req_id = test_arg.run_async(x)
        print(f"[{req_id}] Inference request #{req_id} submitted with user_arg({loop})")
        result_queue.put(req_id)
        unique_id += 1
        if unique_id == len(test_args):
            unique_id = 0
            

    # Wait for all callbacks to complete
    # Join the queue and wait for all tasks to be done
    result_queue.join()

    end_time = time.time()

    total_time = (end_time - start_time) * 1000  # Convert to milliseconds
    avg_latency = total_time / args.loops  # Average latency per request
    fps = 1000.0 / avg_latency  # FPS based on average latency

    print("-----------------------------------")
    print(f"  Total Time: {total_time:.2f} ms")
    print(f"  Average Latency: {avg_latency:.2f} ms")
    print(f"  FPS: {fps:.2f} frames/sec")
    print("-----------------------------------")
