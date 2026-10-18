# Home Assistant 自定义集成：东风奕派车辆状态（dongfeng_yipai）

把「东风奕派」App（包名 `com.dfmc.dfpv.sapp`，v2.1.9）背后的 TSP 云端车辆状态
接入 Home Assistant，并在 Lovelace 仪表盘展示。

## 逆向依据（来自 dongfengyipai_998992.apk 的静态分析）

| 项目 | 值 | 来源 |
|---|---|---|
| 生产网关 | `https://dfypappgw-pros.dfiov.com.cn` | classes.dex 字符串池 |
| 测试网关 | `dfypappgw-sits/uats/perf.dfiov.com.cn` | 同上 |
| 认证域 | `idp-prd.dfiov.com.cn`（`auth/v2/token`、`auth/v1/getVehicleToken`） | 同上 |
| 车辆状态接口 | `GET /msvehiclestatus/vehiclestatus/v3/vehicleStatus`（带定位版 `vehicleStatusWithPoint`） | 同上 |
| 充电启停 | `POST /mscharge/charging/start` / `stop` | 同上 |
| 远控指令 | `POST /msrcs/remote/sendvhlctl` | 同上 |
| 推送上报主题 | `msvehiclestatus/vehiclereport/travelAndCharge`（另有 paho-MQTT 依赖） | 同上 |
| 请求头 | `Authorization` / `X-App-Id` / `X-Auth-Token` / `X-Device-Id` / `X-Client-Version` | 同上 |
| 状态字段 | `powerSocStatus` `chargingStatus` `batteryPackChrgDchrgPower/TimeLength` `chargingPortStatus` `rearViewMirrorStatus` `acCabinTemperature` `tyrePressure.*` 等 | ADS protobuf（`DciCommonStatus.proto` 等 71 份）+ JSON 字段池 |

⚠️ 重要限制：APK 带**爱加密（secneo apkwrapper）加固**，登录/请求签名逻辑在运行时才解密，
`assets/config.json` 等也是密文，因此本集成**不实现自动登录**，需要你从官方 App 抓包
（mitmproxy + 手机装用户 CA；App 启用了证书校验 `usesCleartextTraffic=0` 且有 SSL-pinning 迹象，
可能需要 Frida 绕过）拿到 Bearer token 填入配置。token 过期后需重新抓取。

## 安装

### 方式一：HACS 自定义仓库（推荐）

1. HA → 设置 → 套件与服务（Stores）→ HACS → 右上角 ⋮ → **Custom repositories**。
2. 仓库地址粘贴：`https://github.com/mastertion/ha-dongfeng-yipai`，类别选 **Integration**，添加。
3. 回到 Integrations 列表找到 **东风奕派车辆状态** → 下载（选最新 Release）。
4. 重启 Home Assistant，之后按下面「配置」步骤添加实例。

> 本仓库通过 GitHub Actions 在推送 `v*` tag 时自动发布 Release 并附 HACS 安装包，
> 因此 HACS 能直接读取版本列表，无需手动上传 zip。

### 方式二：手动复制

1. 把 `custom_components/dongfeng_yipai/` 复制到 HA 配置目录的 `custom_components/` 下。
2. 重启 Home Assistant。
3. 设置 → 设备与服务 → 添加集成 → 搜索 **“东风奕派”**：
   - **正式模式**：填网关、VIN、抓到的 token；
   - **演示模式**：通过 `config_flow` 的 demo 步骤或直接把手动 YAML 里 `mock_mode: true`
     （也可在集成目录放一个自动化入口）——最快方式：先不填 token，创建后在
     `.storage/config_entries` 中把 `mock_mode` 置 `true`，即可用内置模拟数据预览全部实体。
4. Lovelace：把 `lovelace/yipai-dashboard.yaml` 中 `cards:` 内容粘贴进一个新视图（手动 YAML 模式）。

## 实体一览（unique id 前缀 = VIN）

| 平台 | 实体 | 说明 |
|---|---|---|
| sensor | yipai_powersocstatus | SOC（DciCommonStatus.powerSocStatus，0-100%） |
| sensor | yipai_endurancemileage / yipai_totalmileage | 剩余续航 / 总里程 km |
| sensor | yipai_charge_power_kw | 充电功率（W→kW） |
| sensor | yipai_batterypackchrgdchrgetimelength | 剩余充电时长（min） |
| sensor | yipai_accabintemperature / yipai_outtemperature | 车内 / 车外温度 |
| sensor | yipai_speed / 四轮胎压 / yipai_updatetime | 车速、kPa、上报时刻 |
| binary_sensor | yipai_charging | chargingStatus==1（1充电中/2完成/3故障/4连接未充电） |
| binary_sensor | yipai_online / yipai_locked / yipai_doors | 在线、门锁、任一车门未关 |
| binary_sensor | yipai_charging_port / yipai_ac_on / yipai_mirror_folded | 充电口盖(0关1开)、空调、后视镜(0折叠) |
| switch | yipai_charge_switch | 启停充电（走 mscharge 接口，需网关额外签名时可能失败） |
| button | yipai_refresh | 立即轮询 |
| device_tracker | yipai_location | GPS（vehicleStatusWithPoint） |

## 适配你抓到的真实报文

字段名如与云端不一致，只改 `sensor.py` / `binary_sensor.py` 里 `DESCRIPTIONS` 的
`key` / `lookup` 即可；鉴权头在 `api.py`；接口路径在 `const.py`。
如果抓包发现状态接口需要 `sign`/`nonce`/`timestamp` 类签名参数，
把签名逻辑（加固壳内，需脱壳后从真实 DEX 还原）或直接把一次抓到的可用请求改造成
固定模板，是目前最现实的路线。

## 免责声明

仅供个人车主在**自己的车辆、自己的账号**上做家庭自动化联动使用；逆向分析限于本地静态
研究，不绕过大厂风控、不共享 token。请遵守东风汽车用户协议与所在地法律法规。
