import sys
import os
sys.path.insert(1, os.path.join(sys.path[0], ".."))
from bo.utils import *
import uuid
import pickle

jax.config.update("jax_enable_x64", True)

class GeneralObjective:
    def __init__(self, gp_restarts,name, expertise, objective_description, obj_type):
        self.expertise = expertise
        self.objective_description = objective_description
        self.obj_type = obj_type
        self.name = name
        dataset_path = "function_creation/datasets/"+self.name+"_dataset.csv"
        self.dataset = pd.read_csv(dataset_path)
        self.x_names = list(self.dataset.columns)[:-1]
        self.y_name = list(self.dataset.columns)[-1]
        self.dim = len(self.x_names)
        self.gp_restarts = gp_restarts
        self.dataset_grouping()
        self.normalize_data()
        self.bounds_setting()
        self.gp = build_gp_dict(*train_gp(self.input_matrix, jnp.array([self.output_matrix]).T, self.gp_restarts))

    def dataset_grouping(self):
        ds_grouped = self.dataset.groupby(self.x_names)[self.y_name].agg(lambda x: x.unique().mean())
        self.dataset = ds_grouped.reset_index()

    def bounds_setting(self):
        self.bounds = np.array([self.dataset.iloc[:, :-1].min().values, self.dataset.iloc[:, :-1].max().values]).T

    def normalize_data(self):
        self.input_matrix = self.dataset.iloc[:, :-1].values 
        self.output_matrix = self.dataset[self.y_name].values
        if self.obj_type == "min":
            self.f_opt = -self.output_matrix.min()
        else:
            self.f_opt = self.output_matrix.max()
        self.input_mean = self.input_matrix.mean(axis=0)
        self.input_std = self.input_matrix.std(axis=0)
        self.output_mean = self.output_matrix.mean()
        self.output_std = self.output_matrix.std()
        self.input_matrix = (self.input_matrix - self.input_mean) / self.input_std
        self.output_matrix = (self.output_matrix - self.output_mean) / self.output_std

    def __call__(self, x):
        x = np.array(x)
        x_n = [float((x[i] - self.input_mean[i]) / self.input_std[i]) for i in range(len(x))]
        m_y, v_y = inference(self.gp, jnp.array([x_n]))
        val = (m_y.item() * self.output_std) + self.output_mean
        if self.obj_type == "min":
            return -val
        else:
            return val


class SelfOpt(GeneralObjective):
    def __init__(self, gp_restarts):
        super().__init__(
            gp_restarts,
            name= "selfopt",
        expertise = "Optimization in chemical reaction conditions.",
        objective_description = '''
        The system represents an exothermic continuous-flow reactor, where the primary focus is on maximizing the final concentration of the desired product while ensuring safety and operational stability. 
        The reactor is characterized by two main input variables: the reactor temperature \( T_w \) and the Damköhler number \( Da \).
        
        \( T_w \) controls the kinetics of the reaction, influencing both the rate and the equilibrium conversion. 
        \( Da \) is a dimensionless number that balances reaction and diffusion rates, effectively affecting how uniformly the reaction proceeds throughout the reactor.

        The objective function \( -\log(x_{\text{para}, \text{end}}) \) aims to maximize the final product concentration by minimizing the negative logarithm of final product concentration. 

        The objective is the value of this negative-log function, which must be minimized.
        ''',
        obj_type = "min")