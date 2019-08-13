# SZENL bot public version

本repository包含了深绿bot的基本框架，删去了部分为深绿社群特质化的内容（如深绿早播报、起田、语录等）。目前包含的功能有：
- 登记特工信息
- 查询官方活动
- 查询社群活动
- 加入/退出活动
- 群发消息（管理员/活动组织者）

各社群可根据自己的需求扩展功能。

受 [Astrian 为成绿写的 IFS bot](https://github.com/Astrian/IFS-RSVP-Bot) 启发，本 bot 以 Airtable 为数据库，并部署在 Heroku 上，各社群亦可根据自己需求改用 SQL 及 Google app engine 等。


## 提前准备
### 环境配置
```
pip install python-telegram-bot==11.1.0
pip install airtable-python-wrapper==0.12.0
```

### 创建 Airtable Base
1. 创建 Airtable base：在 [Airtable](https://airtable.com) 中注册账号，并根据[这个格式](https://airtable.com/shrczfwJeSedTjKqM)创建表格，建议直接点击右上角的“copy base”。
2. 获得 base id：在 base 中点击右上角 Help -> API documentation 获得 base id（即 base key）。
3. 获得 aou key：同样在 API documentation 中，勾选上右上角的“show API kye”，可以在下面的 AUTHENTICATION 中右侧看到自己的 api key。此外，你也可以在自己的账户界面查看到自己的 api key。

### 创建 Heroku App
在 [Heroku](https://www.heroku.com) 创建个 app 并获得 domain 地址 (dashboard -> your bot app -> settings -> domain)。

### 创建 bot
去 Telegram 找 @BotFather 创建个新 bot，并记下 bot 的 api token。

以上准备事项完成后，在 ```configure.py``` 中修改对应参数。


## 部署
将 bot 部署至 Heroku。如部署至其他地方，请记得修改 ```main.py``` 中的 Heroku 相关代码。


## 使用
第一次使用时需要向 bot 发送 /register 指令，bot 会自动在 Airtable 的相关 base 中记录用户的 Username 与 User id。此外，向 bot 发送 /id 也可以快速查询自己的 User id。


## 注意事项
- Heroku 免费用户的 app 会在闲置30分钟后自动断线。如断线，下次启动时间会变长且部分chat data, job data会丢失。如不希望这种事情发生，可以使用 pickle 保存数据，或直接把 bot 部署在其他地方（如 google cloud 的免费虚拟机）。
- 部分用户可能没有设置 User name，扩写程序时需注意这一点，避免程序出错。


## 参考阅读
- [Airtable Python Wrapper Documentation](https://airtable-python-wrapper.readthedocs.io/en/master/)
- [Python Telegram Bot Wrapper](https://github.com/python-telegram-bot/python-telegram-bot)