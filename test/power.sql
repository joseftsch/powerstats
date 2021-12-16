CREATE TABLE IF NOT EXISTS `power202112` (
  `id` int NOT NULL AUTO_INCREMENT,
  `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `current_pv_watt` int NOT NULL,
  `current_consumption_from_grid_watt` float NOT NULL,
  `current_consumption_house_watt` float NOT NULL,
  `energy_pv_today_wh` float NOT NULL,
  `energy_pv_year_wh` float NOT NULL,
  `energy_pv_total_wh` float NOT NULL,
  `autonomy_percent` int NOT NULL,
  `selfconsumption_percent` int NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
COMMIT;
