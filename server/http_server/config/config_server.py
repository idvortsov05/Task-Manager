import configparser


def get_config(config_file_path):
    config = configparser.ConfigParser()
    config.read(config_file_path)
    return config
