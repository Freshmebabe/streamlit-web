import streamlit as st
st.title("简易计算器")
num1 = st.number_input("输入数字1")
num2 = st.number_input("输入数字2")
operation = st.selectbox("选择运算", ["+", "-", "×", "÷"])
if st.button("计算"):
    result = eval(f"{num1} {operation.replace('×','*').replace('÷','/')} {num2}")
    st.success(f"结果: {result}")