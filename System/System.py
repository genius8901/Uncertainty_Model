import os.path
import re
import numpy as np

from Gates.AndGate import AndGate
from Gates.BufferGate import BufferGate
from Gates.InverterGate import InverterGate
from Gates.NandGate import NandGate
from Gates.NorGate import NorGate
from Gates.OrGate import OrGate
from Gates.XorGate import XorGate

SYSTEM_FILE_TYPE: str = '.sys'
SYSTEM_NAME_INDEX: int = 0
INPUTS_INDEX: int = 1
OUTPUTS_INDEX: int = 2
GATES_INDEX: int = 3
OUTPUT_PROBABILITY = 0.9


class System:
    """
    Representing a system base on sys file.
    """

    def __init__(self, path_to_file: str):
        self.outputs = None  # Dic mapping name of system (o1, o2 etc.) to the value (0 or 1). None at beginning
        self.inputs = None  # Dic mapping name of system (i1 i2 etc.) to the value (0 or 1). None at beginning
        self.system_name = None
        self.gates = None  # Dic mapping name of gate (e.g. "gate27") to logic gates
        self.zeds = {}  # Dic mapping the inner wires of the system
        if os.path.isfile(path_to_file) and SYSTEM_FILE_TYPE in path_to_file:
            file = open(path_to_file, 'r')
            file_content = self.read_file(file)
            self.get_system_name(file_content)
            self.init_inputs_dict(file_content)
            self.init_outputs_dict(file_content)
            self.init_gates_dict(file_content)

    @staticmethod
    def parse_obs_files(obs_file_path):
        """
        Reads an .obs file and extracts from each line the inputs and outputs.
        :param obs_file_path: Path to the .obs file
        :return: a dictionary with the different input and output values.
        """
        obs_dict = {}
        with open(obs_file_path, 'r') as obs_file:
            file_str = obs_file.read()
            file_str = file_str.split('.')
            for line in file_str:
                if len(line) <= 1:
                    continue
                index = line.split(',')[1]
                obs_dict[index] = {'inputs': {}, 'outputs': {}}
                wires = line.split('[')[1].split(']')[0]
                wires = wires.replace('\n', '')
                wires = wires.split(',')
                for wire in wires:
                    if wire[0] == '-':  # it's a 0
                        wire = wire.strip('-')
                        if wire[0] == 'i':  # it's an output
                            obs_dict[index]['inputs'][wire] = 0
                        else:
                            obs_dict[index]['outputs'][wire] = 0
                    else:  # it's a 1
                        if wire[0] == 'i':  # it's an output
                            obs_dict[index]['inputs'][wire] = 1
                        else:
                            obs_dict[index]['outputs'][wire] = 1

        return obs_dict

    def calc_system_output(self, input_values, faulty_gates=None):
        """
        Function that calculates the expected outputs given input values.
        :param input_values: A dictionary mapping input index to value, i.e o1 -> 0
        :param faulty_gates: A list of gates that are faulty, i.e. output opposite values (e.g. 1 instead of 0).
        """
        self.clean_system()
        self.inputs = input_values
        for out in self.outputs:
            gate_name = self.extract_correct_gate(out)
            self.outputs[out] = self.calc_gate_output(gate_name, faulty_gates)

        return self.outputs

    def calc_gate_output(self, gate_name, faulty_gates):
        """
        Recursively calculate the gate's output.
        :param gate_name: name of the gate.
        :param faulty_gates: A list of gates that are faulty, i.e. output opposite values (e.g. 1 instead of 0).
        :return: the gate's output.
        """

        gate = self.gates[gate_name]['gate']

        for wire, val in gate.inputs.items():  # Iterate through all required inputs to the gate
            if wire[0] == 'i':  # it's an input, so it must already have a value.
                val = self.inputs[wire]
            else:  # it's a z, therefor we must check if we already calculated it. If not, calculate and update it.
                if wire[0] == 'z' and self.zeds[wire] is not None:  # we have already calculated it.
                    val = self.zeds[wire]
                elif wire[0] == 'o' and self.outputs[wire] is not None:
                    val = self.outputs[wire]
                else:
                    inner_gate_name = self.extract_correct_gate(wire)
                    val = self.calc_gate_output(inner_gate_name, faulty_gates)
                    self.zeds[wire] = val

            gate.inputs[wire] = val

        gate.calculate_output()
        if faulty_gates is not None and gate_name in faulty_gates:
            gate.output = self.flip_bit(gate.output)
        return gate.get_output()

    @staticmethod
    def flip_bit(val):
        if val == 1:
            return 0
        else:
            return 1

    def extract_correct_gate(self, desired_output: str):
        for gate_name, gate in self.gates.items():
            if gate['output'] == desired_output:  # This gate's output is the required wire
                return gate_name

    @staticmethod
    def read_file(file):
        """
        Read the file content and connect it to a single string and split by '.' delimiter
        :param file: file object of the system model
        :return: list of strings. each cell in the list is a parameter of the model: system name,
         inputs, outputs, gates
        """
        file_content = ""
        for line in file:
            line = line.strip()
            file_content += line
        file_content = file_content.split('.')
        return file_content

    def get_system_name(self, file_content: list):
        """
        get the system name from list of the file content
        :param file_content: list of the parameters of the system model.
        the output of read_file method
        """
        self.system_name = file_content[SYSTEM_NAME_INDEX]

    def init_inputs_dict(self, file_content: list):
        """
        Initialize the dictionary of inputs. At the end of the function the input name is the key and the value is None.
        :param file_content: list of parameters of the system model. the output of read_file method
        """
        inputs_str = file_content[INPUTS_INDEX]
        inputs_list = self.line_clean(inputs_str)
        self.inputs = dict.fromkeys(inputs_list)

    @staticmethod
    def line_clean(line: str):
        """
        Clean line of system model file content. remove the characters '[' and ']' and split by the
        delimiter ','
        :param line: line from the system model file
        :return: list of parsed parameters from the line
        """
        line = line.strip('[]')
        line_list = line.split(',')
        return line_list

    def init_outputs_dict(self, file_content):
        """
        Initialize the dictionary of the outputs. key is the name of the output and value is None for each
        output.
        :param file_content: the output of read_file method.
        """
        outputs_str = file_content[OUTPUTS_INDEX]
        outputs = self.line_clean(outputs_str)
        self.outputs = dict.fromkeys(outputs)

    def init_gates_dict(self, file_content):
        """
        Initialize gate dictionary. parsing the output of the system model file.
        key is name of the gate. value is the corresponding gate object.
        Also initialize zeds dictionary (middle output of the system)
        :param file_content:
        :raise: Exception if couldn't find the correct gate type
        """
        gates_def = self.clean_gates_def(file_content[GATES_INDEX])
        self.gates = {}
        for gate_str in gates_def:
            gate_params = self.line_clean(gate_str)
            gate_type, number_of_inputs = self.parse_get_type(gate_params[0])
            gate_name = gate_params[1]
            gate_output = gate_params[2]
            if gate_output not in self.zeds and 'o' not in gate_output:
                self.zeds[gate_output] = None
            if number_of_inputs is not None:
                gate_inputs = self.create_gate_inputs_dict(gate_params, number_of_inputs)
            else:
                gate_inputs = self.create_gate_inputs_dict(gate_params, 1)
            gate = self.build_gate(gate_type, gate_inputs)
            if gate is not None:
                self.gates[gate_name] = {'gate': gate, 'output': gate_output}
            else:
                raise Exception("Gate type: " + gate_type + " is not recognized")

    @staticmethod
    def parse_get_type(logic_type: str):
        """
        parse the first gate parameter.
        :param logic_type: gate_type and number of inputs combined. Like and3
        :return: the gate type and number of inputs separate
        """
        index_of_digit = re.search('[0-9]', logic_type)
        if index_of_digit is not None:
            index_of_digit = index_of_digit.start()
            gate_type = logic_type[:index_of_digit]
            num_of_inputs = int(logic_type[index_of_digit:])
            return gate_type, num_of_inputs
        else:
            return logic_type, None

    @staticmethod
    def create_gate_inputs_dict(gate_params: list, number_of_inputs: int):
        gate_inputs = {}
        for index in range(3, 3 + number_of_inputs):
            input_name = gate_params[index]
            gate_inputs[input_name] = None
        return gate_inputs

    @staticmethod
    def build_gate(gate_type: str, gate_inputs: dict):
        return {
            'and': AndGate(gate_inputs),
            'buffer': BufferGate(gate_inputs),
            'inverter': InverterGate(gate_inputs),
            'nand': NandGate(gate_inputs),
            'nor': NorGate(gate_inputs),
            'or': OrGate(gate_inputs),
            'xor': XorGate(gate_inputs)
        }.get(gate_type, None)

    @staticmethod
    def clean_gates_def(gates_def: str):
        gates_def = gates_def[1:-1]
        return gates_def.split('],')

    @staticmethod
    def generate_output_probabilities(observed_output):
        """
        Receives the observed output and generates a dictionary where the keys are a combination of outputs and the
        values are the probability for such an output.
        :param observed_output: The observed output (e.g. o1 = 0, o2 = 1, o3 = 1)
        :return: A dictionary with all the combinations for outputs and their probabilities. key: a string e.g 00010,
        the value is a floating point representing the probability of this output.
        """

        combo_dict = {}
        output_num = len(observed_output)
        combo_num = pow(2, output_num)
        for i in range(0, combo_num):
            binary = np.binary_repr(i, width=output_num)
            probability = 1
            index = 0
            for char in binary:
                index += 1
                if int(char) == observed_output['o'+str(index)]:
                    probability *= OUTPUT_PROBABILITY
                else:
                    probability *= 1-OUTPUT_PROBABILITY
            combo_dict[binary] = probability

        return combo_dict

    def clean_system(self):

        for zed in self.zeds:
            self.zeds[zed] = None
