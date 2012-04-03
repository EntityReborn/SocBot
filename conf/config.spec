[general]
	commandchars = string(default="!")
	nicktrigger = string(default="true")

[servers]
    [[__many__]]
        host = string()
        port = integer(default=6667)
        nickname = string(default="SocBot")
        [[[channels]]]
        	[[[[__many__]]]]
        		password = string(default="")
        		autojoin = boolean(default=True)
