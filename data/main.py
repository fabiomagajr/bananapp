import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("tabela.csv")
print(df.head())
print(df.info())
print(df.describe())

print(f'Unicos: {df["ID_Cliente"].nunique()}')
clientes_frequentes = df[df["Cliente_Frequente"] == "Sim"]
print(f'Clientes frequentes: {clientes_frequentes}')

df.groupby("Categoria")["Total_Venda"].sum().plot(kind="bar", title="Total de Vendas por Categoria")
plt.ylabel("Total em R$")
plt.show()