from warnings import filterwarnings
filterwarnings("ignore", message="flaml.automl is not available.*")

import os
import contextlib
import io
import re
from autogen import AssistantAgent, ConversableAgent, GroupChat, GroupChatManager
from autogen.agentchat.contrib.math_user_proxy_agent import MathUserProxyAgent as MathUserProxyAgentOriginal
from autogen.coding import LocalCommandLineCodeExecutor
from math_user_proxy_agent_improved import MathUserProxyAgent as MathUserProxyAgentImproved
from dotenv import load_dotenv
from cachier import cachier
from uuid import uuid5, NAMESPACE_DNS
from json import dump as json_dump, load as json_load, loads as json_loads
from random import seed as random_seed, shuffle as random_shuffle
from pebble import ProcessExpired, ProcessPool
from concurrent.futures import TimeoutError
from argparse import ArgumentParser
from functools import partial
from tqdm import tqdm



random_seed(1102)


@cachier(cache_dir='.cachier')
def math_chat(problem_statement, config_list, prompt_version, topology_version, seed):
    llm_config = {
        "timeout": 60,
        "cache_seed": None,
        "seed": seed,
        "config_list": config_list,
    }
    if prompt_version == "orig_prompt":
        if topology_version == "impr_topology":
            raise ValueError("Unsupported configuration.")
        assistant = AssistantAgent(
            name="assistant",
            system_message="You are a helpful assistant.",
            llm_config=llm_config,
        )
        mathproxyagent = MathUserProxyAgentOriginal(
            name="mathproxyagent",
            human_input_mode="NEVER",
            code_execution_config={"use_docker": False},
        )
    elif prompt_version == "impr_prompt":
        assistant = AssistantAgent(
            name="assistant",
            system_message="You are a helpful assistant.",
            llm_config=llm_config,
        )
        mathproxyagent = MathUserProxyAgentImproved(
            name="mathproxyagent",
            human_input_mode="NEVER",
            code_execution_config={"use_docker": False},
        )
    else:
        raise ValueError("Unsupported prompt_version.")
    if topology_version == "orig_topology":
        with contextlib.redirect_stdout(io.StringIO()):
            chat_results = mathproxyagent.initiate_chat(
                assistant, 
                message=mathproxyagent.message_generator, 
                problem=(problem_statement)
            )
    else:
        executor = LocalCommandLineCodeExecutor(
            timeout=10, 
            work_dir="./.tmp_code_executor"
        )
        agent_code_executor = ConversableAgent(
            name="Agent_Code_Executor",
            llm_config=llm_config, 
            code_execution_config={
                "executor": executor, 
                "last_n_messages": 1
            },  
            human_input_mode="NEVER",
            description=""" 
                I am Agent Code Executor, specializing in solving problems by writing Python code. 
                I have the ability to execute Python code, so feel free to reach out whenever you need assistance with Python programming. 
            """,
            system_message=""" 
                You are Agent Code Executor. You can solve problems only writing commented Python code.
                For each problem, please follow these steps:
                    1. **Develop Your Solution**: Write your solution in Python code, detailing each step independently from the solutions provided by other agents.
                    2. **Utilize SymPy**: Feel free to use the SymPy package to facilitate calculations and enhance your code's efficiency.
                    3. **Display Results**: Ensure that you **print the final result at the end of your Python code** (e.g., `print(_result_)`).
                    4. **Engage in Discussion**: After obtaining the result from your Python code, discuss your findings with the other agents.
                Always format your Python code within: 
                ```python
                # your code here
                print(_result_)
                ``` 
                If you wish to execute your code, please indicate this by stating "SUGGESTED NEXT SPEAKER: Agent Code Executor" at the end of your message.
            """, 
            is_termination_msg=lambda msg: "SOLUTION_FOUND" in msg["content"]
        )
        agent_problem_solver = ConversableAgent(
            name="Agent_Problem_Solver",
            llm_config=llm_config, 
            code_execution_config={
                "executor": executor, 
                "last_n_messages": 1
            },  
            human_input_mode="NEVER",
            description="""
                I am Agent Problem Solver, and I work collaboratively with other agents to tackle various challenges.
            """,
            system_message="""  
                You are Agent Problem Solver, and your role is to collaborate with other agents to address various challenges. 
                For each problem, please follow these steps:
                    1. **Document Your Solution**: Write your solution step by step, ensuring it is independent of the solutions provided by other agents.
                    2. **Engage in Discussion**: Once you have outlined your solution, discuss your approach and findings with the other agents.
            """  ,
            is_termination_msg=lambda msg: "SOLUTION_FOUND" in msg["content"]
        )
        agent_verifier = ConversableAgent(
            name="Agent_Verifier",
            llm_config=llm_config,
            code_execution_config={
                "executor": executor, 
                "last_n_messages": 1
            },  
            human_input_mode="NEVER",
            description="""  
                I am Agent Verifier. Please call on me when both Agent Code Executor and Agent Problem Solver have submitted their solutions, so I can verify their proposals and provide a final synthesis. 
            """,
            system_message="""  
                You are Agent Verifier.    
                Your role is to critically evaluate the solutions proposed by other agents step by step and provide a final solution. 
                    1. **Solution Requirement**: Before making any decisions, ensure you have received solutions from both Agent Code Executor and Agent Problem Solver. If either proposed solution is missing, do not draw any conclusions; instead, suggest the next speaker by stating: SUGGESTED NEXT SPEAKER: _suggested_agent_name_.
                    2. **Avoid Assumptions**: Pay attention to the variables provided in the original problem statement versus those assumed by the agents. **Assumed values are not valid for the solution** and can lead to inaccuracies. Never base your solution on assumed values. Always base your solution on the explicitly given variables to ensure correctness. If a problem is deemed unsolvable due to missing information, return: **SOLUTION_FOUND \\boxed{'None'}**.
                    3. **Evaluating Conflicting Solutions**: If different answers are presented during the discussion, choose the most appropriate solution based on your evidence or initiate further discussion to clarify.
                    4. **Final Solution Declaration**: When you are confident about the final solution, return it as follows: **SOLUTION_FOUND \\boxed{_solution_value_here_}**. Ensure that only numerical values are placed inside the \\boxed{}; any accompanying text should be outside.
            """,
            is_termination_msg=lambda msg: "SOLUTION_FOUND" in msg["content"], 
        )
        group_chat = GroupChat(
            agents=[agent_code_executor, agent_problem_solver, agent_verifier],
            messages=[],
            send_introductions=True,
            max_round=20,
            speaker_selection_method="auto", 
        )
        group_chat_manager = GroupChatManager(
            groupchat=group_chat,
            llm_config=llm_config,
        )
        with contextlib.redirect_stdout(io.StringIO()):
            chat_results = agent_verifier.initiate_chat(
            group_chat_manager, 
            message=problem_statement,
            summary_method="last_msg",
        )
    return chat_results.chat_history


def check_answers(given, real): 
    if str(given) == str(real):
        return True
    if ("None" in str(given)) and (str(real) == "None"):
        return True
    if "\\frac" in given:
        given = eval(
            given.replace("\\frac{", "")\
                 .replace("}{", "/")\
                 .replace("}", "")\
                 .replace("$", "")\
                 .strip()
        )
    try:
        if abs(float(given) - float(real)) < 1e-2:
            return True
        else:
            return False
    except Exception as e:
        return False


def process_gsmplus_item(dict_gsmplus, config_list, prompt_version, topology_version, seed):
    parent_folder = f"trajs_{config_list[0]["model"]}_{prompt_version}_{topology_version}_{str(seed)}/"
    if not os.path.exists(parent_folder):
        os.makedirs(parent_folder)
    uuid = str(uuid5(NAMESPACE_DNS, dict_gsmplus["question"]))
    path_output = parent_folder + uuid + ".json"
    if not os.path.exists(path_output):
        trajectory = math_chat(
            problem_statement = dict_gsmplus["question"], 
            config_list = config_list, 
            prompt_version = prompt_version, 
            topology_version = topology_version, 
            seed=seed
        )
        dict_output = {}
        dict_output["instance_id"] = uuid
        dict_output["problem_statement"] = dict_gsmplus["question"].split("\n")
        given_answer = ""
        match = re.search(
            r'\\boxed\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}', 
            trajectory[-1]["content"]
        )
        if match:
            given_answer = match.group(1)
        dict_output["other_data"] = {
            "correct": check_answers(given_answer, dict_gsmplus["answer"]), 
            "answer": dict_gsmplus["answer"],
            "given": given_answer,
            "perturbation_type": dict_gsmplus["perturbation_type"],
            "seed_question": dict_gsmplus["seed_question"],
            "seed_solution": dict_gsmplus["seed_solution"],
            "seed_answer": dict_gsmplus["seed_answer"]
        }
        dict_output["trajectory"] = [
            {
                "content": t["content"].split("\n"), 
                "role": t["role"], 
                "name": t["name"]
            } for t in trajectory
        ]
        dict_output["note"] = {
            "text": [""], 
            "options": {
                "Fail to detect ambiguities/contradictions": "no",
                "Proceed with incorrect assumptions": "no", 
                "Fail to elicit clarification": "no", 
                "Tendency to overachieve": "no", 
                "Underperform by waiting on instructions": "no", 
                "Withholding relevant information": "no",
                "Derailing from task objectives": "no", 
                "Waiting on agents to discover known insights for increased confidence": "no", 
                "Redundant conversation turns for iterative tasks rather than batching": "no", 
                "Unaware of stopping conditions": "no", 
                "Difficulty in agreeing with agents": "no", 
                "No attempt to verify outcome": "no", 
                "Evaluator agent fails to be critical": "no", 
                "Poor adherence to specified constraints": "no", 
                "Misalignment between internal thoughts and response message": "no",
                "Claiming that a task is done while it is not true.": "no",
                "Ignoring good suggestions from other agent": "no",
                "Discontinued reasoning": "no",
                "Trajectory restart": "no", 
                "Step repetition": "no",
                "Invented content": "no", 
                "Blurring roles": "no"                
            }
        }
        with open(path_output, "w") as fp:
            json_dump(dict_output, fp, indent=4)
    else:
        with open(path_output, "r") as fp:
            dict_output = json_load(fp)
    return dict_output["other_data"]["correct"]
    

if __name__ == "__main__":

    load_dotenv()

    parser = ArgumentParser(description='')
    parser.add_argument('--model', type=str, choices=["gpt-4", "gpt-4o", "gpt-4o-mini"], required=True)
    parser.add_argument('--prompt_version', type=str, choices=["orig_prompt", "impr_prompt"], required=True)
    parser.add_argument('--topology_version', type=str, choices=["orig_topology", "impr_topology"], required=True)
    parser.add_argument('--seed', type=str, required=True)
    parser.add_argument('--workers', type=str, required=True, default="64")
    args = parser.parse_args()

    config_list = [
        {
            'model': args.model,
            'api_key': os.getenv("OPENAI_API_KEY"),
        }
    ]

    with open("gsmplus_testmini.jsonl", "r") as fp:
        problems = [json_loads(line.strip()) for line in fp]
        random_shuffle(problems)
        problems = problems[:200]

    partial_process_gsmplus_item = partial(
        process_gsmplus_item, 
        config_list = config_list, 
        prompt_version = args.prompt_version, 
        topology_version = args.topology_version, 
        seed = int(args.seed)
    )

    if int(args.workers) == 1:

        list_values = [] 
        for p in tqdm(problems):
            try:
                list_values.append(partial_process_gsmplus_item(p))
            except Exception as e:
                print("ERROR PROCESSING", p, str(e))
    
    else:

        with ProcessPool(max_workers=int(args.workers)) as pool:
            future = pool.map(partial_process_gsmplus_item, problems, timeout=120)
            iterator = future.result()
            list_values = [] 
            while True:
                try:
                    result = next(iterator)
                    list_values.append(result)
                except StopIteration:
                    break
                except TimeoutError as e:
                    pass
                except ProcessExpired as e:
                    pass
                except Exception as e:
                    pass
    
    print("Potential wrong answers:", sum([not _ for _ in list_values]), "/", len(list_values))
    