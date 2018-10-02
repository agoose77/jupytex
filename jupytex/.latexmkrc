add_cus_dep('hash', 'tex', 0, 'execute_code');
sub execute_code {
   return system("jupytex-execute \"$_[0]\"");
}
