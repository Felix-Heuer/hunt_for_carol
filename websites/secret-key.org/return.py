import base64

text = """We were just a group of raccoons, doing our thing, when we spotted something special: you. We needed to test you, so we set up a series of cryptographic puzzles, hoping you'd be sharp enough to crack them. And you did. The next thing we knew, you were in: our world, our mission, and trust me, we needed you. Things escalated fast when a rival gang of raccoons came at us full force. We couldn't let them win.

That's when Carol stepped in. Working at SHA2.org and feeding us intel through you, helping us keep the upper paw. She was our secret weapon. But just when we thought we had everything under control, she vanished. No warning, no trace.

It's been too long, and I can't shake the feeling that something's wrong. Carol's still out there, hiding, and I need to know why. This is not a drill like our games, this one's real and is going to be tough!

Let's star our investigation at the SHA2 organization. Apply for a job in cryptography at sha2.org, get inside, and let's uncover the truth. Time to dig deep, figure out what happened - and bring Carol back!

        ..                         ..        
       :@@@#+.                 .=#@@@-       
       *@=-*@@#---------------*@@#=:@%       
       *@-  :#@#             +@%-  .@%       
       :@*    .               .    =@=       
        =@:                       .@*        
        .#            :            *.        
  .:   -*  ...        %        ...  +-   :.  
  *=---.  .@@@@%+-=  -@+  :=+%@@@@-   :--:*  
  ==  .:=#@@@@@@@@@#=@@@=*@@@@@@@@@#=:.  :+  
  -#: :@@@@@@@**#@@@@%##@@@@%**@@@@@@@= .#-  
  -@*: :%@@@@@@*==%@-   :%@+=*@@@@@@@- .+%=  
   :*.   +@@@@@@@@%.      #@@@@@@@@*.   +-   
     ++.   =#@@@@-.       ..@@@@%=.   =+.    
       =+=: .+**%.   %*%:   %#*+: .-==.      
         -#@%=  -*   .+-   ==  -#@#-         
            :-----==*@@@#==-----:"""

def string_to_binary(text):
    return ' '.join(format(ord(char), '08b') for char in text)

def encode_base64(text):
    # Convert string to bytes
    text_bytes = text.encode()
    # Encode to Base64
    base64_bytes = base64.b64encode(text_bytes)
    # Convert bytes back to string
    return base64_bytes.decode()


ascii_bits = string_to_binary(text)
b64 = encode_base64(ascii_bits)

inlay = {
    "START_TEXT": b64
}

with open("return-template.html","r",encoding="utf-8") as fp:
    template = fp.read()

html_code = template.format(**inlay)

with open("return.html", "w", encoding="utf-8") as f:
    f.write(html_code)


print("Written")