import numpy as np
import pandas as pd
from scipy.stats import norm, uniform, bernoulli, expon
from scipy.optimize import root_scalar

def generate_dynamic_copula_data(target_corr_matrix, marginal_ppfs, column_names=None, num_samples=100000):
    """
    Generuje próbę skorelowanych zmiennych losowych za pomocą metody Copula Gaussa.

    Parametry:
    target_corr_matrix (numpy.ndarray): Macierz N x N docelowych współczynników korelacji Pearsona
    marginal_ppfs (list of callables): Lista N funkcji, każda funkcja musi akceptować macierz prawdopodobieństw
                                        w [0,1] i zwracać odpowiedni kwantyl
    column_names (list of str, optional): Nazwy kolumn (zmiennych) do zapisu w pd dataframe
    num_samples (int): liczba wierszy do wygenerowania

    Returns:
    pd.DataFrame: Tabela zawierająca wyniki symulacji - skorelowane wartości zmiennych losowych
    """
    # Sprawdzanie inputu
    n_vars = len(marginal_ppfs)
    if target_corr_matrix.shape != (n_vars, n_vars):
        raise ValueError(f"Matrix shape {target_corr_matrix.shape} does not match the number of PPFs ({n_vars}).")
    
    if column_names is None:
        column_names = [f"Var_{i+1}" for i in range(n_vars)]
    elif len(column_names) != n_vars:
        raise ValueError("Length of column_names must match the number of PPFs.")

    # kalibracja korelacji na pojedynczej parze zmiennych
    def _calibrate_correlation(target_corr, dist1_ppf, dist2_ppf, size=200000):
        if target_corr == 0.0:
            return 0.0
            
        np.random.seed(42)
        Z1 = np.random.normal(0, 1, size)
        Z_indep = np.random.normal(0, 1, size)
        
        def objective(rho):
            Z2 = rho * Z1 + np.sqrt(1 - rho**2) * Z_indep
            X1 = dist1_ppf(norm.cdf(Z1))
            X2 = dist2_ppf(norm.cdf(Z2))
            return np.corrcoef(X1, X2)[0, 1] - target_corr

        try:
            res = root_scalar(objective, bracket=[-0.99, 0.99], method='brentq')
            return res.root
        except ValueError:
            # Jeśli zadana macierz korelacji jest matematycznie nieosiągalna dla zadanych rozkładów, error
            raise ValueError(f"Zadana macierz korelacji: {target_corr} jest niemożliwa do osiągnięcia.")

    # Budowanie pierwotnej macierzy korelacji
    print(f"Calibrating {n_vars}x{n_vars} matrix...")
    calibrated_R = np.eye(n_vars)
    
    for i in range(n_vars):
        for j in range(i + 1, n_vars):
            target_rho = target_corr_matrix[i, j]
            calib_rho = _calibrate_correlation(target_rho, marginal_ppfs[i], marginal_ppfs[j])
            
            calibrated_R[i, j] = calib_rho
            calibrated_R[j, i] = calib_rho

    # Generowanie skorelowanych zmiennych normalnych
    print("Generowanie danych symulacyjnych...")
    np.random.seed(None)
    
    mvn_samples = np.random.multivariate_normal(np.zeros(n_vars), cov=calibrated_R, size=num_samples)
    
    # Mapping na rozkład jednostajny na [0,1]
    u_samples = norm.cdf(mvn_samples)

    # Zamianna skorelowanych zmiennych na rozkłady docelowe
    df_dict = {}
    for i in range(n_vars):
        col_name = column_names[i]
        ppf_func = marginal_ppfs[i]
        
        df_dict[col_name] = ppf_func(u_samples[:, i])

    print("Zakończono generowanie symulacji\n")
    return pd.DataFrame(df_dict)


# ==========================================
# Example Usage with Dynamic Callables
# ==========================================
if __name__ == "__main__":
    
    # 1. Define a 4x4 Target Matrix
    target_matrix = np.array([
        [1.0,  0.2, -0.4,  0.1],
        [0.2,  1.0,  0.5,  0.0],
        [-0.4, 0.5,  1.0,  0.3],
        [0.1,  0.0,  0.3,  1.0]
    ])
    
    # 2. Define the list of PPF functions (using lambda or wrappers)
    my_ppfs = [
        lambda u: uniform(loc=1000, scale=9000).ppf(u), # Var 1: Uniform(1000, 10000)
        lambda u: bernoulli(p=0.1).ppf(u),              # Var 2: Bernoulli(p=0.1)
        lambda u: norm(loc=50, scale=10).ppf(u),        # Var 3: Normal(50, 10)
        lambda u: expon(scale=5).ppf(u)                 # Var 4: Exponential(lambda=1/5)
    ]
    
    # 3. Define nice column names
    my_columns = ["Salary_Uniform", "WakeUp_Bernoulli", "Age_Normal", "WaitTime_Expon"]
    
    # 4. Generate!
    df_sim = generate_dynamic_copula_data(
        target_corr_matrix=target_matrix,
        marginal_ppfs=my_ppfs,
        column_names=my_columns,
        num_samples=100000
    )
    
    # Verify the results
    print("--- First 5 Rows ---")
    print(df_sim.head().round(2), "\n")
    
    print("--- Final Output Correlation Matrix ---")
    print(df_sim.corr().round(2))