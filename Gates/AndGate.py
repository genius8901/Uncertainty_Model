from Gates.Gate import Gate


class AndGate (Gate):

    def __init__(self, inputs: dict, gate_name: str = ""):
        self.inputs = inputs
        self.calculate_output()
        self.name = gate_name

    def calculate_output(self):
        value = 1
        for input_value in self.inputs.values():
            if input_value == 0:
                value = 0
                break
        self.output = value

    def get_output(self):
        return self.output

    def get_inputs(self):
        return self.inputs

    def get_input(self, key: str):
        return self.inputs.get(key)

    def set_input(self, key: str, value: int):
        self.inputs[key] = value
        self.calculate_output()

    def get_name(self):
        return self.name

