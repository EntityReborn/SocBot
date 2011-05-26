[general]

[permtemplates]
    [[__many__]]
        permissions = list()

[users]
	[[__many__]]
		passhash = string()
		permissions = list(default=list())
		email = string()
