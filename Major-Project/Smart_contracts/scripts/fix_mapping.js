const { Web3 } = require('web3');
const fs = require('fs');

async function fixMapping() {
  const web3 = new Web3('http://127.0.0.1:7545');
  const accounts = await web3.eth.getAccounts();
  const adminAccount = accounts[0];
  const officerAccount = '0x4266Accd5AAc953c4Bb30c32a008606C2D851EAa'; // Dept 200 Officer from DB
  
  const artifact = JSON.parse(fs.readFileSync('build/contracts/LandRegistry.json', 'utf8'));
  const abi = artifact.abi;
  const address = artifact.networks['5777'].address;
  
  const contract = new web3.eth.Contract(abi, address);
  
  console.log("Mapping Dept 200 to", officerAccount, "...");
  
  try {
    await contract.methods.mapRevenueDeptIdToEmployee(200, officerAccount).send({
      from: adminAccount,
      gas: 500000
    });
    console.log("SUCCESS! Mapped on blockchain.");
  } catch (error) {
    console.error("FAILED to map:", error.message);
  }
}

fixMapping();
