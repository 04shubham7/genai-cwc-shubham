import tiktoken

enc = tiktoken.encoding_for_model("gpt-4o")

text = "Hello, world!"
tokens = enc.encode(text) 

print("Tokens:", tokens)

Tokens= [13225, 11, 2375, 0]

decoded=enc.decode(Tokens)

print("Decoded:", decoded)