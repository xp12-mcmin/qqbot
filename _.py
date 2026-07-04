import sys
sys.set_int_max_str_digits(0)

p = 1
for i in range(1, 3001):
    p = p * i
p = p * p * p  # (3000!)^3

# 写入文件
with open("result.txt", "w", encoding="utf-8") as f:
    f.write(str(p))

print("计算完成！结果已保存到 result.txt")
