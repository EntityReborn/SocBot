[general]
	commandchars = string(default='!')
	nicktrigger = string(default="true")
	permerrornotification = option(PM, NOTICE, CHANNEL, default=NOTICE)
	
[logging]
    level = option(DEBUG, INFO, WARNING, ERROR, EXCEPTION, default=WARNING)

[servers]
    [[__many__]]
        host = string()
        port = integer(default=6667)
        nickname = string(default="SocBot")
        [[[channels]]]
        	[[[[__many__]]]]
        		password = string(default="")
        		autojoin = boolean(default=True)
        		kickedrejoin = boolean(default=True)
        		
[directories]
    plugins = string(default="plugins")
    plugindata = string(default="data")
    logs = string(default="logs")
