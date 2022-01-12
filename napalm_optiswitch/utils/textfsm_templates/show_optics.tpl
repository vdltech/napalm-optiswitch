# Chassis value will be null for single chassis routers.
Value Port (\d+)
Value LaserBias (-?\d+.\d+)
Value TxPower (-?\d+.\d+)
Value RxPower (-?\d+.\d+)


Start
  ^\s+Port[ \t]+${Port}
  ^\s+TX Bias        \(mA\):[ \t]+${LaserBias}
  ^\s+Tx Power \(dBm\)\/\(mW\):[ \t]+${TxPower}
  ^\s+Rx Power \(dBm\)\/\(mW\):[ \t]+${RxPower} -> Record