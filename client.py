#!/usr/bin/env python3
import jupter_client


client = jupter_client.BlockingKernelClient(connection_file)
client.load_connection_file()
client.start_channels()