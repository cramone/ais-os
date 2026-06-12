<Query Kind="Statements">
  <Connection>
    <ID>172c85b3-e9e0-4e61-8149-f1d359663a81</ID>
    <NamingServiceVersion>2</NamingServiceVersion>
    <Persist>true</Persist>
    <Server>localhost</Server>
    <AllowDateOnlyTimeOnly>true</AllowDateOnlyTimeOnly>
    <DeferDatabasePopulation>true</DeferDatabasePopulation>
    <Database>export</Database>
    <SqlSecurity>true</SqlSecurity>
    <UserName>sa</UserName>
    <Password>AQAAANCMnd8BFdERjHoAwE/Cl+sBAAAAgtTO3wq6wUu6Jc/tv++WRAAAAAACAAAAAAAQZgAAAAEAACAAAAD/3C8k3u8vfqCOnY8oUMxL2RKFAqlYTVwWs6g+4djVTgAAAAAOgAAAAAIAACAAAAAGNyOoaqlwkivfl8mih7T6Z7a2INFw2WJOqYFykctc3CAAAADMP6UsbPACFO/zrYOJbVMUeBozbuAmliEtKuZb6zoW9UAAAAANJJtrLYn2S1JALnbquv5W7M5Ml272HM0ILzqHr80p27ktoPwAnZUsRWCZ4LurZmv3uV6WHWPy5ZKuOYMG1d5q</Password>
    <NoPluralization>true</NoPluralization>
    <NoCapitalization>true</NoCapitalization>
    <DriverData>
      <LegacyMFA>false</LegacyMFA>
    </DriverData>
  </Connection>
  <Namespace>System.Text.Json.Serialization</Namespace>
  <Namespace>System.Text.Json</Namespace>
</Query>

var filePath = @"c:\Users\chase\OneDrive\Magiq\AIS-OS\projects\magiq-media\files\export\MAGIQ_DOCS_export.json";
if (File.Exists(filePath)){
	File.Delete(filePath);
}

using var fileStream = new FileStream(filePath, FileMode.Append, FileAccess.Write, FileShare.Read);
using var writer = new StreamWriter(fileStream, Encoding.UTF8);

var profileName = "Documents";
var rows = new List<MEDIA_DOCS>();
int? documentId = null;
foreach(var row in MEDIA_DOCS.OrderBy(d => d.DOCUMENT_ID).ThenBy(d => d.ROWNBR))
{
	if (documentId is null){
		documentId = row.DOCUMENT_ID;
	}
	var hitNextDocument = documentId != row.DOCUMENT_ID;
	if (hitNextDocument) {
		writer.WriteLine(JsonSerializer.Serialize(JsonMediaItemEntry.Build(profileName, rows)));
		rows.Clear();
	}	
	
	rows.Add(row);
}

if (rows.Count > 0){
	writer.WriteLine(JsonSerializer.Serialize(JsonMediaItemEntry.Build(profileName, rows)));
}


public sealed class JsonMediaItemEntry
{
	[JsonPropertyName("assets")]
	public List<JsonMediaItemAsset> Assets { get; set; }

	[JsonPropertyName("author")]
	public string Author { get; set; }

	[JsonPropertyName("recordDate")]
	public DateTimeOffset? RecordDate { get; set; }

	[JsonPropertyName("description")]
	public string Description { get; set; }

	[JsonPropertyName("folderPath")]
	public string FolderPath { get; set; }

	[JsonPropertyName("profileId")]
	public string ProfileName { get; set; }

	[JsonPropertyName("title")]
	public string Title { get; set; }

	[JsonPropertyName("metadata")]
	public List<JsonMediaItemMetadataBatch> Metadata { get; set; }
	
	private const string NullString = "NULL";
	
	private static bool IsNullOrWhiteSpace(string value){
		return string.IsNullOrWhiteSpace(value) || string.Equals(value, NullString, StringComparison.OrdinalIgnoreCase);
	}
	
	public static JsonMediaItemEntry Build(string profileName, List<MEDIA_DOCS> rows){
		var metadata = new List<JsonMediaItemMetadataBatch>();
		var ordered = rows.OrderBy(row => int.Parse(row.ROWNBR)).ToList();
		foreach(var row in ordered) {
			var batch = new JsonMediaItemMetadataBatch();
			batch.AttributedTo = row.CPSETSAVEDBYNAME;
			if (!string.IsNullOrWhiteSpace(row.CPSETSAVEDDATE) && DateTime.TryParse(row.CPSETSAVEDDATE, out var attributedDate)) {
				batch.AttributedDate = attributedDate;	
			}
			
			batch.Fields = [];
			
			if (!IsNullOrWhiteSpace(row.CUSTOMER_ID)) {
				batch.Fields.Add(nameof(MEDIA_DOCS.CUSTOMER_ID), JsonSerializer.SerializeToElement(int.Parse(row.CUSTOMER_ID)));	
			}
			
			if (!IsNullOrWhiteSpace(row.HOUSE_LOCATION)) {
				batch.Fields.Add(nameof(MEDIA_DOCS.HOUSE_LOCATION), JsonSerializer.SerializeToElement(int.Parse(row.HOUSE_LOCATION)));	
			}
						
			if (!IsNullOrWhiteSpace(row.LETTER_NAME)) {
				batch.Fields.Add(nameof(MEDIA_DOCS.LETTER_NAME), JsonSerializer.SerializeToElement(row.LETTER_NAME));
			}

			if (!IsNullOrWhiteSpace(row.OWNER_ID)) {
				batch.Fields.Add(nameof(MEDIA_DOCS.OBJECTID), JsonSerializer.SerializeToElement(int.Parse(row.OBJECTID)));
			}
			
			if (!IsNullOrWhiteSpace(row.OBJECTTYPE)) {
				batch.Fields.Add(nameof(MEDIA_DOCS.OBJECTTYPE), JsonSerializer.SerializeToElement(int.Parse(row.OBJECTTYPE)));	
			}
			
			if (!IsNullOrWhiteSpace(row.OWNER_ID)) {
				batch.Fields.Add(nameof(MEDIA_DOCS.OWNER_ID), JsonSerializer.SerializeToElement(row.OWNER_ID));
			}
			
			if (!IsNullOrWhiteSpace(row.STREET_ID)) {
				batch.Fields.Add(nameof(MEDIA_DOCS.STREET_ID), JsonSerializer.SerializeToElement(int.Parse(row.STREET_ID)));	
			}
			
			if (!IsNullOrWhiteSpace(row.VALUATION_ID)) {
				batch.Fields.Add(nameof(MEDIA_DOCS.VALUATION_ID), JsonSerializer.SerializeToElement(row.VALUATION_ID));	
			}
			
			if (!IsNullOrWhiteSpace(row.APPLICANT_NAME)) {
				batch.Fields.Add(nameof(MEDIA_DOCS.APPLICANT_NAME), JsonSerializer.SerializeToElement(row.APPLICANT_NAME));	
			}
			
			if (!IsNullOrWhiteSpace(row.CONSENT_ID)) {
				batch.Fields.Add(nameof(MEDIA_DOCS.CONSENT_ID), JsonSerializer.SerializeToElement(row.CONSENT_ID));	
			}
			
			if (!IsNullOrWhiteSpace(row.PROPERTY_ID)) {
				batch.Fields.Add(nameof(MEDIA_DOCS.PROPERTY_ID), JsonSerializer.SerializeToElement(int.Parse(row.PROPERTY_ID)));	
			}
			
			if (!IsNullOrWhiteSpace(row.PROPOSAL)) {
				batch.Fields.Add(nameof(MEDIA_DOCS.PROPOSAL), JsonSerializer.SerializeToElement(row.PROPOSAL));	
			}
			
			if (!IsNullOrWhiteSpace(row.RA_LOCATION)) {
				batch.Fields.Add(nameof(MEDIA_DOCS.RA_LOCATION), JsonSerializer.SerializeToElement(row.RA_LOCATION));	
			}

			if (!IsNullOrWhiteSpace(row.CE_ID)) {
				batch.Fields.Add(nameof(MEDIA_DOCS.CE_ID), JsonSerializer.SerializeToElement(int.Parse(row.CE_ID)));
			}
			
			if (!IsNullOrWhiteSpace(row.CEMETERY_CODE)) {
				batch.Fields.Add(nameof(MEDIA_DOCS.CEMETERY_CODE), JsonSerializer.SerializeToElement(row.CEMETERY_CODE));	
			}
			
			if (!IsNullOrWhiteSpace(row.DATE_OF_DEATH)) {
				batch.Fields.Add(nameof(MEDIA_DOCS.DATE_OF_DEATH), JsonSerializer.SerializeToElement(DateTime.Parse(row.DATE_OF_DEATH)));	
			}
			
			if (!IsNullOrWhiteSpace(row.DATE_OF_INTERMENT)) {
				batch.Fields.Add(nameof(MEDIA_DOCS.DATE_OF_INTERMENT), JsonSerializer.SerializeToElement(DateTime.Parse(row.DATE_OF_INTERMENT)));
			}
			
			if (!IsNullOrWhiteSpace(row.FIRST_NAMES)) {
				batch.Fields.Add(nameof(MEDIA_DOCS.FIRST_NAMES), JsonSerializer.SerializeToElement(row.FIRST_NAMES));
			}

			if (!IsNullOrWhiteSpace(row.SURNAME))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.SURNAME), JsonSerializer.SerializeToElement(row.SURNAME));
			}

			if (!IsNullOrWhiteSpace(row.COMPLIANCE_SCHEDULE_ID))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.COMPLIANCE_SCHEDULE_ID), JsonSerializer.SerializeToElement(row.COMPLIANCE_SCHEDULE_ID));
			}

			if (!IsNullOrWhiteSpace(row.CREDITOR_ID))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.CREDITOR_ID), JsonSerializer.SerializeToElement(int.Parse(row.CREDITOR_ID)));
			}

			if (!IsNullOrWhiteSpace(row.FULL_NAME))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.FULL_NAME), JsonSerializer.SerializeToElement(row.FULL_NAME));
			}

			if (!IsNullOrWhiteSpace(row.APPLICATION_ACCOUNT_ID))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.APPLICATION_ACCOUNT_ID), JsonSerializer.SerializeToElement(row.APPLICATION_ACCOUNT_ID));
			}

			if (!IsNullOrWhiteSpace(row.APPLICATION_ID))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.APPLICATION_ID), JsonSerializer.SerializeToElement(row.APPLICATION_ID));
			}

			if (!IsNullOrWhiteSpace(row.DEBT_MANAGEMENT_ID))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.DEBT_MANAGEMENT_ID), JsonSerializer.SerializeToElement(int.Parse(row.DEBT_MANAGEMENT_ID)));
			}

			if (!IsNullOrWhiteSpace(row.DM_NAME_KEY))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.DM_NAME_KEY), JsonSerializer.SerializeToElement(row.DM_NAME_KEY));
			}

			if (!IsNullOrWhiteSpace(row.DEBTOR_ID))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.DEBTOR_ID), JsonSerializer.SerializeToElement(row.DEBTOR_ID));
			}

			if (!IsNullOrWhiteSpace(row.ACCOUNT_ID))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.ACCOUNT_ID), JsonSerializer.SerializeToElement(row.ACCOUNT_ID));
			}

			if (!IsNullOrWhiteSpace(row.DEBTOR_NAME))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.DEBTOR_NAME), JsonSerializer.SerializeToElement(row.DEBTOR_NAME));
			}

			if (!IsNullOrWhiteSpace(row.LEDGER))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.LEDGER), JsonSerializer.SerializeToElement(row.LEDGER));
			}

			if (!IsNullOrWhiteSpace(row.MASTERFILE_UNIQUE_ID))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.MASTERFILE_UNIQUE_ID), JsonSerializer.SerializeToElement(row.MASTERFILE_UNIQUE_ID));
			}

			if (!IsNullOrWhiteSpace(row.INFRINGEMENT_ID))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.INFRINGEMENT_ID), JsonSerializer.SerializeToElement(int.Parse(row.INFRINGEMENT_ID)));
			}

			if (!IsNullOrWhiteSpace(row.OWNER_NAME))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.OWNER_NAME), JsonSerializer.SerializeToElement(row.OWNER_NAME));
			}

			if (!IsNullOrWhiteSpace(row.GL_ID))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.GL_ID), JsonSerializer.SerializeToElement(int.Parse(row.GL_ID)));
			}

			if (!IsNullOrWhiteSpace(row.GL_NAME))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.GL_NAME), JsonSerializer.SerializeToElement(row.GL_NAME));
			}

			if (!IsNullOrWhiteSpace(row.INVOICE_DATE))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.INVOICE_DATE), JsonSerializer.SerializeToElement(DateTime.Parse(row.INVOICE_DATE)));
			}

			if (!IsNullOrWhiteSpace(row.INVOICE_ID))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.INVOICE_ID), JsonSerializer.SerializeToElement(row.INVOICE_ID));
			}

			if (!IsNullOrWhiteSpace(row.INVOICE_NUMBER))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.INVOICE_NUMBER), JsonSerializer.SerializeToElement(int.Parse(row.INVOICE_NUMBER)));
			}

			if (!IsNullOrWhiteSpace(row.BUSINESS_DETAIL))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.BUSINESS_DETAIL), JsonSerializer.SerializeToElement(row.BUSINESS_DETAIL));
			}

			if (!IsNullOrWhiteSpace(row.LICENCE_DETAIL))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.LICENCE_DETAIL), JsonSerializer.SerializeToElement(row.LICENCE_DETAIL));
			}

			if (!IsNullOrWhiteSpace(row.LICENCE_ID))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.LICENCE_ID), JsonSerializer.SerializeToElement(row.LICENCE_ID));
			}

			if (!IsNullOrWhiteSpace(row.LICENSEE_NAME))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.LICENSEE_NAME), JsonSerializer.SerializeToElement(row.LICENSEE_NAME));
			}

			if (!IsNullOrWhiteSpace(row.LOCATION))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.LOCATION), JsonSerializer.SerializeToElement(row.LOCATION));
			}

			if (!IsNullOrWhiteSpace(row.LIM_ID))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.LIM_ID), JsonSerializer.SerializeToElement(row.LIM_ID));
			}

			if (!IsNullOrWhiteSpace(row.PROJECT_ID))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.PROJECT_ID), JsonSerializer.SerializeToElement(row.PROJECT_ID));
			}

			if (!IsNullOrWhiteSpace(row.PROJECT_NAME))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.PROJECT_NAME), JsonSerializer.SerializeToElement(row.PROJECT_NAME));
			}

			if (!IsNullOrWhiteSpace(row.RG_LEGAL_DESCRIPTION))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.RG_LEGAL_DESCRIPTION), JsonSerializer.SerializeToElement(row.RG_LEGAL_DESCRIPTION));
			}

			if (!IsNullOrWhiteSpace(row.RG_LOCATION))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.RG_LOCATION), JsonSerializer.SerializeToElement(row.RG_LOCATION));
			}

			if (!IsNullOrWhiteSpace(row.LEGAL_DESCRIPTION))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.LEGAL_DESCRIPTION), JsonSerializer.SerializeToElement(row.LEGAL_DESCRIPTION));
			}

			if (!IsNullOrWhiteSpace(row.RATEPAYER_NAME_1))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.RATEPAYER_NAME_1), JsonSerializer.SerializeToElement(row.RATEPAYER_NAME_1));
			}

			if (!IsNullOrWhiteSpace(row.RATEPAYER_NAME_2))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.RATEPAYER_NAME_2), JsonSerializer.SerializeToElement(row.RATEPAYER_NAME_2));
			}

			if (!IsNullOrWhiteSpace(row.RA_LEGAL_DESCRIPTION))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.RA_LEGAL_DESCRIPTION), JsonSerializer.SerializeToElement(row.RA_LEGAL_DESCRIPTION));
			}

			if (!IsNullOrWhiteSpace(row.REBATE_ID))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.REBATE_ID), JsonSerializer.SerializeToElement(int.Parse(row.REBATE_ID)));
			}

			if (!IsNullOrWhiteSpace(row.CALLER_NAME))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.CALLER_NAME), JsonSerializer.SerializeToElement(row.CALLER_NAME));
			}

			if (!IsNullOrWhiteSpace(row.RECORD_ID))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.RECORD_ID), JsonSerializer.SerializeToElement(int.Parse(row.RECORD_ID)));
			}

			if (!IsNullOrWhiteSpace(row.CUSTOMER_NAME))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.CUSTOMER_NAME), JsonSerializer.SerializeToElement(row.CUSTOMER_NAME));
			}

			if (!IsNullOrWhiteSpace(row.WATER_ID))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.WATER_ID), JsonSerializer.SerializeToElement(int.Parse(row.WATER_ID)));
			}

			if (!IsNullOrWhiteSpace(row.SourceTable))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.SourceTable), JsonSerializer.SerializeToElement(row.SourceTable));
			}

			batch.Fields.Add(nameof(MEDIA_DOCS.DOCUMENT_ID), JsonSerializer.SerializeToElement(row.DOCUMENT_ID));

			if (!IsNullOrWhiteSpace(row.DOCUMENT_OWNER))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.DOCUMENT_OWNER), JsonSerializer.SerializeToElement(row.DOCUMENT_OWNER));
			}

			if (!IsNullOrWhiteSpace(row.DOCUMENT_TYPE))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.DOCUMENT_TYPE), JsonSerializer.SerializeToElement(row.DOCUMENT_TYPE));
			}

			if (!IsNullOrWhiteSpace(row.DOCUMENT_SOURCE))
			{
				batch.Fields.Add(nameof(MEDIA_DOCS.DOCUMENT_SOURCE), JsonSerializer.SerializeToElement(row.DOCUMENT_SOURCE));
			}

			batch.Fields.Add(nameof(MEDIA_DOCS.FOLDER_ID), JsonSerializer.SerializeToElement(row.FOLDER_ID));

			if (metadata.Contains(batch))
			{
				continue;
			}
			
			metadata.Add(batch);
		}
		

		var item = new JsonMediaItemEntry
		{
			Assets = new List<JsonMediaItemAsset>
			{
				new JsonMediaItemAsset {
					Name = rows[0].DOCUMENT_NAME,
					Path = rows[0].WH_PATH.Trim(),
					Role = "Primary"
				}
			},
			Author = rows[0].DOCUMENT_AUTHOR,
			Description = rows[0].DOCUMENT_DESCRIPTION,
			FolderPath = rows[0].FOLDER_PATH,
			ProfileName = "Documents",
			Metadata = metadata,
			RecordDate = rows[0].DOCUMENT_REGISTERDATE,
			Title = rows[0].DOCUMENT_NAME
		};
		
		return item;
	}
}

public sealed class JsonMediaItemMetadataBatch
{
	[JsonPropertyName("fields")]
	public Dictionary<string, JsonElement> Fields { get; set; }

	[JsonPropertyName("attributedTo")]
	public string AttributedTo { get; set; }

	[JsonPropertyName("attributedDate")]
	public DateTimeOffset? AttributedDate { get; set; }
}

public sealed class JsonMediaItemAsset
{
	[JsonPropertyName("name")]
	public string Name { get; set; }

	[JsonPropertyName("path")]
	public string Path { get; set; }

	[JsonPropertyName("role")]
	public string Role { get; set; }
}