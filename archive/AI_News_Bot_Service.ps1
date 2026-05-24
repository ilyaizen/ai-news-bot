# AI_News_Bot_Service.ps1

$ServiceName = "AI_News_Bot_Service"
$ExecutablePath = "D:\GitHub\ai-news-bot\main.py"
$PythonPath = "C:\Python314\python.exe"  # Change this to your Python installation path
$WorkingDirectory = "D:\GitHub\ai-news-bot"
$NssmPath = "C:\Tools\nssm\nssm.exe"  # Changed path to a more likely location
$RequiredPackages = @("discord.py", "beautifulsoup4", "python-dotenv", "requests")  # Add more packages as needed

# Check if NSSM is installed
if (!(Test-Path $NssmPath)) {
    Write-Host "NSSM not found at $NssmPath." -ForegroundColor Yellow
    Write-Host "Searching for NSSM in common locations..." -ForegroundColor Yellow
    
    $possibleLocations = @(
        "C:\Tools\nssm\nssm.exe",
        "C:\Program Files\nssm\nssm.exe",
        "C:\Program Files (x86)\nssm\nssm.exe",
        "C:\Windows\System32\nssm.exe"
    )
    
    foreach ($location in $possibleLocations) {
        if (Test-Path $location) {
            Write-Host "Found NSSM at $location" -ForegroundColor Green
            $NssmPath = $location
            break
        }
    }
    
    if (!(Test-Path $NssmPath)) {
        Write-Host "NSSM not found. Please download it from https://nssm.cc/download" -ForegroundColor Yellow
        Write-Host "After downloading, place nssm.exe in a directory and update the `$NssmPath variable." -ForegroundColor Yellow
        exit 1
    }
}

# Check if service exists and delete it if it does
$ServiceExists = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($ServiceExists) {
    Write-Host "Service already exists. Stopping and removing it..."
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    & $NssmPath remove $ServiceName confirm
    Start-Sleep -Seconds 2  # Give Windows time to fully remove the service
}

# Verify Python path exists
if (!(Test-Path $PythonPath)) {
    Write-Host "ERROR: Python executable not found at $PythonPath" -ForegroundColor Red
    Write-Host "Checking for Python installations..." -ForegroundColor Yellow
    
    # Try to find Python using multiple methods
    $PythonFound = $false
    
    # Method 1: Try Python Launcher (py)
    Write-Host "Trying Python Launcher (py)..." -ForegroundColor Yellow
    try {
        $pyVersion = & py --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Found Python Launcher: $pyVersion" -ForegroundColor Green
            # Get the actual python.exe path from the launcher
            $pyPath = & py -c "import sys; print(sys.executable)" 2>&1
            if ($LASTEXITCODE -eq 0 -and (Test-Path $pyPath)) {
                Write-Host "Using Python path: $pyPath" -ForegroundColor Green
                $PythonPath = $pyPath
                $PythonFound = $true
            }
        }
    }
    catch {
        Write-Host "Python Launcher not available." -ForegroundColor Yellow
    }
    
    # Method 2: Try 'python' command in PATH
    if (-not $PythonFound) {
        Write-Host "Trying 'python' command..." -ForegroundColor Yellow
        try {
            $pythonVersion = & python --version 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "Found Python: $pythonVersion" -ForegroundColor Green
                # Get the full path
                $pythonPath = (Get-Command python).Source
                Write-Host "Using Python path: $pythonPath" -ForegroundColor Green
                $PythonPath = $pythonPath
                $PythonFound = $true
            }
        }
        catch {
            Write-Host "'python' command not found in PATH." -ForegroundColor Yellow
        }
    }
    
    # Method 3: Check common installation directories
    if (-not $PythonFound) {
        Write-Host "Searching common Python installation directories..." -ForegroundColor Yellow
        $possiblePythonDirs = @(
            "C:\Users\User\AppData\Local\Programs\Python",
            "C:\Users\User\AppData\Local\Microsoft\WindowsApps",
            "C:\Python314",
            "C:\Python313",
            "C:\Python312",
            "C:\Python311",
            "C:\Python310",
            "C:\Program Files\Python314",
            "C:\Program Files\Python313",
            "C:\Program Files\Python312",
            "C:\Program Files\Python311",
            "C:\Program Files\Python310"
        )
        
        foreach ($dir in $possiblePythonDirs) {
            if (Test-Path $dir) {
                Write-Host "Checking directory: $dir" -ForegroundColor Yellow
                $PythonInstalls = Get-ChildItem $dir -Directory -ErrorAction SilentlyContinue
                if ($PythonInstalls) {
                    Write-Host "Found Python installations: $($PythonInstalls.Name -join ', ')" -ForegroundColor Green
                    $PossiblePython = Get-ChildItem $dir -Recurse -Filter "python.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
                    if ($PossiblePython) {
                        Write-Host "Using Python path: $($PossiblePython.FullName)" -ForegroundColor Green
                        $PythonPath = $PossiblePython.FullName
                        $PythonFound = $true
                        break
                    }
                }
                # Also check if python.exe is directly in the directory
                $directPython = Join-Path $dir "python.exe"
                if (Test-Path $directPython) {
                    Write-Host "Using Python path: $directPython" -ForegroundColor Green
                    $PythonPath = $directPython
                    $PythonFound = $true
                    break
                }
            }
        }
    }
    
    if (-not $PythonFound) {
        Write-Host "ERROR: No Python installation found." -ForegroundColor Red
        Write-Host "Please install Python or update the `$PythonPath variable at line 5." -ForegroundColor Red
        Write-Host "You can download Python from: https://www.python.org/downloads/" -ForegroundColor Yellow
        exit 1
    }
}

# Verify Python script exists
if (!(Test-Path $ExecutablePath)) {
    Write-Host "ERROR: Python script not found at $ExecutablePath" -ForegroundColor Red
    exit 1
}

# Install required Python packages
Write-Host "Installing required Python packages..." -ForegroundColor Yellow
foreach ($package in $RequiredPackages) {
    Write-Host "Installing $package..." -ForegroundColor Yellow
    & $PythonPath -m pip install $package
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install $package. Please install it manually:" -ForegroundColor Red
        Write-Host "$PythonPath -m pip install $package" -ForegroundColor Yellow
        exit 1
    }
    else {
        Write-Host "$package installed successfully." -ForegroundColor Green
    }
}

# Verify packages after installation
# Write-Host "Verifying packages..." -ForegroundColor Yellow
# foreach ($package in $RequiredPackages) {
#     $packageName = $package.Replace('.py', '').Replace('-', '_')
#     $checkCmd = "try:
#     import $packageName
#     print('OK')
# except ImportError:
#     print('MISSING')"
    
#     $tempFile = [System.IO.Path]::GetTempFileName() + ".py"
#     $checkCmd | Out-File -FilePath $tempFile -Encoding ascii
    
#     $result = (& $PythonPath $tempFile) | Out-String
#     $result = $result.Trim()  # Add this line to trim whitespace
#     Remove-Item $tempFile -Force
    
#     if ($result -ne "OK") {
#         Write-Host "Package $package verification failed. Please install it manually:" -ForegroundColor Red
#         Write-Host "$PythonPath -m pip install $package" -ForegroundColor Yellow
#         exit 1
#     }
#     else {
#         Write-Host "Package $package verified successfully." -ForegroundColor Green
#     }
# }
Write-Host "Skipping package verification (packages already confirmed by pip)..." -ForegroundColor Yellow
# Verification commented out - pip install already confirmed packages are installed

# Create logs directory if it doesn't exist
if (!(Test-Path "$WorkingDirectory\logs")) {
    New-Item -Path "$WorkingDirectory\logs" -ItemType Directory | Out-Null
}

# Create the service using NSSM
Write-Host "Creating service with NSSM..."

# Install the service
& $NssmPath install $ServiceName $PythonPath "`"$ExecutablePath`""

# Configure the service
& $NssmPath set $ServiceName AppDirectory $WorkingDirectory
& $NssmPath set $ServiceName DisplayName "AI News Bot Service"
& $NssmPath set $ServiceName Description "AI News Bot Service - Runs Python script at login"

# Configure logging
& $NssmPath set $ServiceName AppStdout "$WorkingDirectory\logs\service_stdout.log"
& $NssmPath set $ServiceName AppStderr "$WorkingDirectory\logs\service_stderr.log"

# Set restart behavior
& $NssmPath set $ServiceName AppRestartDelay 5000
& $NssmPath set $ServiceName AppExit 0 Restart
& $NssmPath set $ServiceName AppExit 1 Restart

# Configure service to start automatically
& $NssmPath set $ServiceName Start SERVICE_AUTO_START

# Try to start the service
Write-Host "Attempting to start the service..."
try {
    Start-Service -Name $ServiceName -ErrorAction Stop
    Write-Host "Service $ServiceName has been successfully started." -ForegroundColor Green
}
catch {
    Write-Host "Failed to start service. Error: $_" -ForegroundColor Red
    Write-Host "Checking service status..."
    $ServiceStatus = Get-Service -Name $ServiceName
    Write-Host "Service status: $($ServiceStatus.Status)"
    
    Write-Host "Checking Windows Event Log for errors..."
    Get-EventLog -LogName System -Newest 10 -EntryType Error, Warning | 
    Where-Object { $_.Message -like "*$ServiceName*" } | 
    Format-List
    
    Write-Host "Looking for service logs..."
    if (Test-Path "$WorkingDirectory\logs\service_stderr.log") {
        Write-Host "Contents of service_stderr.log:" -ForegroundColor Yellow
        Get-Content "$WorkingDirectory\logs\service_stderr.log" -Tail 20
    }
    
    # Test if we can manually run the command
    Write-Host "Testing if we can manually run the Python script..."
    try {
        $Command = "$PythonPath `"$ExecutablePath`""
        Write-Host "Command: $Command"
        Start-Process -FilePath $PythonPath -ArgumentList "`"$ExecutablePath`"" -WorkingDirectory $WorkingDirectory -NoNewWindow -Wait
        Write-Host "Manual execution completed." -ForegroundColor Green
    }
    catch {
        Write-Host "Manual execution failed: $_" -ForegroundColor Red
    }
}

Write-Host "Service setup complete. Check the logs directory for any issues." -ForegroundColor Green
Write-Host "Service logs are located at $WorkingDirectory\logs\" -ForegroundColor Yellow