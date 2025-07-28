# main.tf

# 1. Specify the Google Cloud Provider
# This block tells Terraform which cloud provider to use and how to authenticate.
# Ensure your gcloud CLI is authenticated and configured for the correct project.
terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
      version = "~> 5.0" # Use a compatible version
    }
  }
}

# 2. Configure the Google Cloud Project and Region/Zone
# You can define these as variables or hardcode them.
# Using variables makes your code more reusable.
variable "project_id" {
  description = "The Google Cloud Project ID."
  type        = string
  default     = "gcp-study-463918" # <<< REMEMBER TO CHANGE THIS
}

variable "region" {
  description = "The Google Cloud region to deploy resources in."
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The Google Cloud zone to deploy the VM in."
  type        = string
  default     = "us-central1-c"
}

provider "google" {
  project = var.project_id
  region  = var.region
  credentials = "${file("gcp-study-463918-73034e695420.json")}"
}

# 3. Define the Compute Engine VM Instance
# This resource block declares a VM instance.
resource "google_compute_instance" "example_vm" {
  name         = "my-terraform-vm"
  machine_type = "e2-medium"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11" # Specify a public image
    }
  }

  network_interface {
    network = "default" # Use the default VPC network
    access_config {
      # This block creates an ephemeral external IP address
    }
  }

  # Optional: Add a startup script to install Nginx
  metadata_startup_script = <<-EOF
    #!/bin/bash
    sudo apt-get update
    sudo apt-get install -y nginx
    echo "<h1>Hello from Terraform!</h1>" | sudo tee /var/www/html/index.nginx-debian.html
    sudo systemctl start nginx
    sudo systemctl enable nginx
  EOF

  tags = ["http-server"] # Apply tags for firewall rules
}

# 4. Define a Firewall Rule to Allow HTTP Traffic
# This is crucial if you want to access the web server on the VM.
resource "google_compute_firewall" "allow_http" {
  name    = "allow-http-from-terraform"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["80"]
  }

  source_ranges = ["0.0.0.0/0"] # Allow from anywhere (for demonstration)
  target_tags   = ["http-server"] # Apply to VMs with this tag
}

# 5. Output the VM's External IP Address
# This makes it easy to find the VM after deployment.
output "vm_external_ip" {
  value       = google_compute_instance.example_vm.network_interface[0].access_config[0].nat_ip
  description = "The external IP address of the deployed VM."
}


